# Copyright © 2012 Jakub Wilk <jwilk@jwilk.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import codecs
import collections
import email.utils
import inspect
import itertools
import os
import re
import urllib.parse

import polib

from lib import gettext
from lib import ling
from lib import misc
from lib import tags

class EnvironmentNotPatched(RuntimeError):
    pass

class PolibCodecs(object):

    # This class substitutes the codecs module for polib, in order to work
    # around a newline decoding bug:
    # http://bugs.debian.org/692283

    def __getattr__(self, attr):
        return getattr(codecs, attr)

    def open(self, path, mode, encoding):
        if mode != 'rU':
            raise NotImplementedError
        with open(path, 'rb') as file:
            for line in file:
                yield line.decode(encoding)

class MetadataStr(str):
    def __iadd__(self, other):
        return MetadataStr(str.__add__(self, other))

class MetadataDict(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.duplicates = {}

    def __setitem__(self, key, value):
        if isinstance(value, MetadataStr):
            dict.__setitem__(self, key, value)
            return
        try:
            orig_value = self[key]
        except KeyError:
            dict.__setitem__(self, key, MetadataStr(value))
        else:
            try:
                self.duplicates[key] += value
            except KeyError:
                self.duplicates[key] = [orig_value, value]

_escapes_re = re.compile(r''' ( \\
(?: [ntbrfva]
  | \\
  | "
  | [0-9]{1,3}
  | x[0-9a-fA-F]{1,2}
  ))+
''', re.VERBOSE)

_short_x_escape_re = re.compile(r'''
    \\x ([0-9a-fA-F]) (?= \\ | $ )
''', re.VERBOSE)

def polib_unescape(s):
    def unescape(match):
        s = match.group()
        s = _short_x_escape_re.sub(r'\x0\1', s)
        result = eval("b'{}'".format(s))
        try:
            return result.decode('ASCII')
        except UnicodeDecodeError:
            # an ugly hack to discover encoding of the PO file:
            parser_stack_frame = inspect.stack()[2][0]
            parser = parser_stack_frame.f_locals['self']
            encoding = parser.instance.encoding
            return result.decode(encoding)
    return _escapes_re.sub(unescape, s)

find_unusual_characters = re.compile(
    r'[\x00-\x08\x0b-\x1a\x1c-\x1f]' # C0 except TAB, LF, ESC
    r'|\x1b(?!\[)' # ESC, except when followed by [
    r'|\x7f' # DEL
    r'|[\x80-\x9f]' # C1
     '|\ufffd' # REPLACEMENT CHARACTER
     '|[\ufffe\uffff]' # non-characters
    r'|(?<=\w)\xbf' # INVERTED QUESTION MARK but only directly after a letter
).findall

class Checker(object):

    _patched_environment = False

    @classmethod
    def patch_environment(cls, encinfo):
        # Install extra encodings that used by real-world PO/MO files, but are
        # not known to Python.
        encinfo.install_extra_encodings()
        # Do not allow broken/missing encoding declarations, unless the file is
        # ASCII-only:
        polib.default_encoding = 'ASCII'
        # Work around a newline decoding bug:
        polib.codecs = PolibCodecs()
        # Detect metadata duplicates:
        orig_base_file_init = polib._BaseFile.__init__
        def base_file_init(self, *args, **kwargs):
            orig_base_file_init(self, *args, **kwargs)
            assert type(self.metadata) is dict
            assert len(self.metadata) == 0
            self.metadata = MetadataDict()
        polib._BaseFile.__init__ = base_file_init
        # Work around an escape sequence decoding bug
        # <https://bitbucket.org/izi/polib/issue/31>:
        polib.unescape = polib_unescape
        cls._patched_environment = True

    def __init__(self, path, *, options):
        if not self._patched_environment:
            raise EnvironmentNotPatched
        self.path = path
        self.fake_path = path
        if options.fake_root is not None:
            (real_root, fake_root) = options.fake_root
            if not real_root.endswith(os.sep):
                raise ValueError
            if not fake_root.endswith(os.sep):
                raise ValueError
            if path.startswith(real_root):
                self.fake_path = fake_root + path[len(real_root):]
        self.options = options

    @misc.not_overridden
    def tag(self, tagname, *extra):
        return

    def check(self):
        # If a file passed to polib doesn't exist, it will “helpfully” treat it
        # as PO/MO file _contents_. This is definitely not what we want. To
        # prevent such disaster, fail early if the file doesn't exit.
        try:
            os.stat(self.path)
        except EnvironmentError as exc:
            self.tag('os-error', tags.safestr(exc.strerror))
            return
        extension = os.path.splitext(self.path)[-1]
        is_template = False
        if extension == '.po':
            constructor = polib.pofile
        elif extension == '.pot':
            constructor = polib.pofile
            is_template = True
        elif extension in ('.mo', '.gmo'):
            constructor = polib.mofile
        else:
            self.tag('unknown-file-type')
            return
        broken_encoding = False
        try:
            try:
                file = constructor(self.path)
            except UnicodeDecodeError as exc:
                broken_encoding = exc
                file = constructor(self.path, encoding='ISO-8859-1')
        except IOError as exc:
            message = str(exc)
            if exc.errno is not None:
                self.tag('os-error', tags.safestr(exc.strerror))
                return
            elif message.startswith('Invalid mo '):
                self.tag('invalid-mo-file')
                return
            elif message.startswith('Syntax error in po file '):
                message = message[24:]
                message_parts = []
                if message.startswith(self.path + ' '):
                    message = message[len(self.path)+1:]
                match = re.match(r'^\(line ([0-9]+)\)(?:: (.+))?$', message)
                if match is not None:
                    lineno_part = 'line {}'.format(match.group(1))
                    message = match.group(2)
                    if message is not None:
                        lineno_part += ':'
                        if re.match(r'^[a-z]+( [a-z]+)*$', message):
                            message = tags.safestr(message)
                    message_parts += [tags.safestr(lineno_part)]
                if message is not None:
                    message_parts += [message]
                self.tag('syntax-error-in-po-file', *message_parts)
                return
            raise
        finally:
            if broken_encoding:
                self.tag('broken-encoding',
                    tags.safestr(repr(broken_encoding.object)[1:]),
                    tags.safestr('cannot be decoded as'),
                    broken_encoding.encoding.upper(),
                )
                broken_encoding = True
        language = self.check_language(file, is_template=is_template)
        self.check_plurals(file, is_template=is_template, language=language)
        encoding = self.check_mime(file, is_template=is_template, language=language)
        if broken_encoding:
            encoding = None
        self.check_dates(file, is_template=is_template)
        self.check_project(file)
        self.check_translator(file, is_template=is_template)
        self.check_headers(file)
        self.check_messages(file, encoding=encoding)

    def check_language(self, file, *, is_template):
        if is_template:
            if not 'Language' in file.metadata:
                self.tag('no-language-header-field')
            return
        language = self.options.language
        linginfo = self.options.linginfo
        language_source = 'command-line'
        if language is None:
            path_components = os.path.normpath(self.path).split('/')
            try:
                i = path_components.index('LC_MESSAGES')
            except ValueError:
                i = 0
            if i > 0:
                language = path_components[i - 1]
                try:
                    language = linginfo.parse_language(language)
                    language.fix_codes()
                    language.remove_encoding()
                    language.remove_nonlinguistic_modifier()
                except ling.LanguageError:
                    # It's not our job to report possible errors in _pathnames_.
                    language = None
                else:
                    language_source = 'pathname'
            del path_components, i
        if language is None and self.path.endswith('.po'):
            language, ext = os.path.splitext(os.path.basename(self.path))
            assert ext == '.po'
            try:
                language = linginfo.parse_language(language)
                if language.encoding is not None:
                    # It's very likely that something else has been confused
                    # for the apparent encoding.
                    raise ling.LanguageError
                language.fix_codes()
                language.remove_nonlinguistic_modifier()
            except ling.LanguageError:
                # It's not our job to report possible errors in _pathnames_.
                language = None
            else:
                language_source = 'pathname'
        meta_language = orig_meta_language = file.metadata.get('Language')
        if meta_language:
            try:
                meta_language = linginfo.parse_language(meta_language)
            except ling.LanguageError:
                try:
                    new_meta_language = linginfo.get_language_for_name(meta_language)
                except LookupError:
                    new_meta_language = None
                if new_meta_language:
                    self.tag('invalid-language', orig_meta_language, '=>', new_meta_language)
                else:
                    self.tag('invalid-language', orig_meta_language)
                meta_language = new_meta_language
        if meta_language:
            if meta_language.remove_encoding():
                self.tag('encoding-in-language-header-field', orig_meta_language)
                prev_meta_language = str(meta_language)
            if meta_language.remove_nonlinguistic_modifier():
                self.tag('language-variant-does-not-affect-translation', orig_meta_language)
                prev_meta_language = str(meta_language)
            try:
                if meta_language.fix_codes():
                    self.tag('invalid-language', orig_meta_language, '=>', meta_language)
            except ling.LanguageError:
                self.tag('invalid-language', orig_meta_language)
                meta_language = None
        if meta_language:
            if language is None:
                language = meta_language
                language_source = 'Language header field'
            elif language != meta_language:
                self.tag('language-disparity',
                    language, tags.safestr('({})'.format(language_source)),
                    '!=',
                    meta_language, tags.safestr('(Language header field)')
                )
        poedit_language = file.metadata.get('X-Poedit-Language')
        if poedit_language:
            # FIXME: This should take also X-Poedit-Country into account.
            try:
                poedit_language = linginfo.get_language_for_name(poedit_language)
            except LookupError:
                self.tag('unknown-poedit-language', poedit_language)
            else:
                if language is None:
                    language = poedit_language
                    language_source = 'X-Poedit-Language header field'
                elif language.language_code != poedit_language.language_code:
                    self.tag('language-disparity',
                        language, tags.safestr('({})'.format(language_source)),
                        '!=',
                        poedit_language, tags.safestr('(X-Poedit-Language header field)')
                    )
        if language is None:
            if not orig_meta_language:
                self.tag('no-language-header-field')
            self.tag('unable-to-determine-language')
            return
        if not orig_meta_language:
            self.tag('no-language-header-field', tags.safestr('Language:'), language)
        return language

    def check_plurals(self, file, *, is_template, language):
        correct_plural_forms = None
        if language is not None:
            correct_plural_forms = language.get_plural_forms()
        if correct_plural_forms is not None:
            assert gettext.parse_plural_forms(correct_plural_forms)
        plural_forms = file.metadata.get('Plural-Forms')
        expected_nplurals = {}
        for message in get_interesting_messages(file):
            if message.msgid_plural:
                expected_nplurals[len(message.msgstr_plural)] = message
                if len(expected_nplurals) > 1:
                    break
        if len(expected_nplurals) > 1:
            args = []
            for n, message in sorted(expected_nplurals.items()):
                args += [n, message_repr(message, template='({})'), '!=']
            self.tag('inconsistent-number-of-plural-forms', *args[:-1])
        if correct_plural_forms is not None:
            plural_forms_hint = correct_plural_forms
        else:
            plural_forms_hint = 'nplurals=<n>; plural=<expression>'
            if len(expected_nplurals) == 1:
                [n] = expected_nplurals.keys()
                plural_forms_hint.replace('<n>', str(n))
        if plural_forms is None:
            if expected_nplurals:
                self.tag('no-plural-forms-header-field', 'Plural-Forms: ' + plural_forms_hint)
            return
        if is_template:
            if expected_nplurals:
                self.tag('no-plural-forms-header-field')
            return
        try:
            (n, expr) = gettext.parse_plural_forms(plural_forms)
        except gettext.PluralFormsSyntaxError:
            self.tag('syntax-error-in-plural-forms', plural_forms, '=>', plural_forms_hint)
        else:
            if len(expected_nplurals) == 1:
                [expected_nplurals] = expected_nplurals.keys()
                if n != expected_nplurals:
                    self.tag('incorrect-number-of-plural-forms',
                        n, tags.safestr('(Plural-Forms header field)'), '!=',
                        expected_nplurals, tags.safestr('(number of msgstr items)')
                    )

    def check_mime(self, file, *, is_template, language):
        mime_version = file.metadata.get('MIME-Version')
        if mime_version is not None:
            if mime_version != '1.0':
                self.tag('invalid-mime-version', mime_version, '=>', '1.0')
        else:
            self.tag('no-mime-version-header-field', tags.safestr('MIME-Version: 1.0'))
        cte = file.metadata.get('Content-Transfer-Encoding')
        if cte is not None:
            if cte != '8bit':
                self.tag('invalid-content-transfer-encoding', cte, '=>', '8bit')
        else:
            self.tag('no-content-transfer-encoding-header-field', tags.safestr('Content-Transfer-Encoding: 8bit'))
        ct = file.metadata.get('Content-Type')
        encoding = None
        if ct is not None:
            match = re.match('^text/plain; charset=([^\s;]+)$', ct)
            if match:
                encinfo = self.options.encinfo
                encoding = match.group(1)
                try:
                    is_ascii_compatible = encinfo.is_ascii_compatible_encoding(encoding)
                except LookupError:
                    if is_template and (encoding == 'CHARSET'):
                        pass
                    else:
                        self.tag('unknown-encoding', encoding)
                    encoding = None
                else:
                    if not is_ascii_compatible:
                        self.tag('non-ascii-compatible-encoding', encoding)
                    elif encinfo.is_portable_encoding(encoding):
                        pass
                    else:
                        new_encoding = encinfo.propose_portable_encoding(encoding)
                        if new_encoding is not None:
                            self.tag('non-portable-encoding', encoding, '=>', new_encoding)
                        else:
                            self.tag('non-portable-encoding', encoding)
                    if language is not None:
                        unrepresentable_characters = language.get_unrepresentable_characters(encoding)
                        if unrepresentable_characters:
                            self.tag('unrepresentable-characters', encoding, *unrepresentable_characters)
            else:
                self.tag('invalid-content-type', ct, '=>', 'text/plain; charset=<encoding>')
        else:
            self.tag('no-content-type-header-field', tags.safestr('Content-Type: text/plain; charset=<encoding>'))
        return encoding

    def check_dates(self, file, *, is_template):
        for field in 'POT-Creation-Date', 'PO-Revision-Date':
            date = file.metadata.get(field)
            if date is None:
                self.tag('no-date-header-field', field)
                continue
            elif is_template and field.startswith('PO-') and (date == 'YEAR-MO-DA HO:MI+ZONE'):
                continue
            fixed_date = gettext.fix_date_format(date)
            if fixed_date is None:
                self.tag('invalid-date', tags.safestr(field + ':'), date)
                continue
            elif date != fixed_date:
                self.tag('invalid-date', tags.safestr(field + ':'), date, '=>', fixed_date)
            stamp = gettext.parse_date(fixed_date)
            if stamp > misc.utc_now():
                self.tag('date-from-future', tags.safestr(field + ':'), date)
            if stamp < gettext.epoch:
                self.tag('ancient-date', tags.safestr(field + ':'), date)

    def check_project(self, file):
        project_id_version = file.metadata.get('Project-Id-Version')
        if project_id_version is None:
            self.tag('no-project-id-version-header-field')
        elif project_id_version == 'PACKAGE VERSION':
            self.tag('boilerplate-in-project-id-version', project_id_version)
        else:
            if not re.search(r'[A-Za-z]', project_id_version):
                self.tag('no-package-name-in-project-id-version', project_id_version)
            if not re.search(r'[0-9]', project_id_version):
                self.tag('no-version-in-project-id-version', project_id_version)
        report_msgid_bugs_to = file.metadata.get('Report-Msgid-Bugs-To')
        if not report_msgid_bugs_to:
            self.tag('no-report-msgid-bugs-to-header-field')
        else:
            real_name, email_address  = email.utils.parseaddr(report_msgid_bugs_to)
            if '@' not in email_address:
                uri = urllib.parse.urlparse(report_msgid_bugs_to)
                if uri.scheme == '':
                    self.tag('invalid-report-msgid-bugs-to', report_msgid_bugs_to)
            elif email_address == 'EMAIL@ADDRESS':
                self.tag('boilerplate-in-report-msgid-bugs-to', report_msgid_bugs_to)

    def check_translator(self, file, *, is_template):
        translator = file.metadata.get('Last-Translator')
        if translator is None:
            self.tag('no-last-translator-header-field')
        else:
            translator_name, translator_email = email.utils.parseaddr(translator)
            if '@' not in translator_email:
                self.tag('invalid-last-translator', translator)
            elif translator_email == 'EMAIL@ADDRESS':
                if not is_template:
                    self.tag('boilerplate-in-last-translator', translator)
        team = file.metadata.get('Language-Team')
        if team is None:
            self.tag('no-language-team-header-field')
        else:
            team_name, team_email = email.utils.parseaddr(team)
            if '@' not in team_email:
                # TODO: An URL is also allowed here.
                # self.tag('invalid-language-team', translator)
                pass
            elif team_email in {'LL@li.org', 'EMAIL@ADDRESS'}:
                if not is_template:
                    self.tag('boilerplate-in-language-team', team)
            else:
                try:
                    team_is_translator = team_email == translator_email
                except NameError:
                    pass
                else:
                    if team_is_translator:
                        self.tag('language-team-equal-to-last-translator', team, translator)

    def check_headers(self, file):
        for key in sorted(file.metadata):
            if key.startswith('X-'):
                continue
            if key not in self.options.gettextinfo.po_header_fields:
                self.tag('unknown-header-field', key)
        try:
            duplicates = file.metadata.duplicates
        except AttributeError:
            pass
        else:
            for key in sorted(duplicates):
                self.tag('duplicate-header-field', key)

    def check_messages(self, file, *, encoding):
        if encoding is None:
            return
        encinfo = self.options.encinfo
        found_unusual_characters = set()
        msgid_counter = collections.Counter()
        for message in get_interesting_messages(file):
            msgid_uc = set(find_unusual_characters(message.msgid))
            msgstr_uc = set(find_unusual_characters(message.msgstr))
            uc = msgstr_uc - msgid_uc - found_unusual_characters
            if uc:
                names = ', '.join(
                    'U+{:04X} {}'.format(ord(ch), encinfo.get_character_name(ch))
                    for ch in sorted(uc)
                )
                self.tag('unusual-character-in-translation', tags.safestr(names + ':'), message.msgstr)
                found_unusual_characters |= uc
            msgid_counter[message.msgid, message.msgctxt] += 1
            if msgid_counter[message.msgid, message.msgctxt] == 2:
                self.tag('duplicate-message-definition', message_repr(message))

def message_repr(message, template='{}'):
    subtemplate = 'msgid {id}'
    kwargs = dict(id=message.msgid)
    if message.msgctxt is not None:
        subtemplate += ' msgctxt {ctxt}'
        kwargs.update(ctxt=message.msgctxt)
    template = template.format(subtemplate)
    return tags.safe_format(template, **kwargs)

def get_interesting_messages(file):
    return itertools.chain(
        file.translated_entries(),
        file.untranslated_entries(),
    )

# vim:ts=4 sw=4 et
