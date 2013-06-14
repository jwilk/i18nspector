# Copyright © 2012, 2013 Jakub Wilk <jwilk@jwilk.net>
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

import collections
import contextlib
import difflib
import email.utils
import os
import re
import struct
import urllib.parse

import polib

from lib import gettext
from lib import ling
from lib import misc
from lib import polib4us
from lib import rfc2606
from lib import tags

class EnvironmentNotPatched(RuntimeError):
    pass

class EnvironmentAlreadyPatched(RuntimeError):
    pass

find_unusual_characters = re.compile(
    r'[\x00-\x08\x0b-\x1a\x1c-\x1f]'  # C0 except TAB, LF, ESC
    r'|\x1b(?!\[)'  # ESC, except when followed by [
    r'|\x7f'  # DEL
    r'|[\x80-\x9f]'  # C1
     '|\ufffd'  # REPLACEMENT CHARACTER
     '|[\ufffe\uffff]'  # non-characters
    r'|(?<=\w)\xbf'  # INVERTED QUESTION MARK but only directly after a letter
).findall

class Checker(object):

    _patched_environment = None

    @classmethod
    @contextlib.contextmanager
    def patched_environment(cls, encinfo):
        if cls._patched_environment is not None:
            raise EnvironmentAlreadyPatched
        cls._patched_environment = False
        with polib4us.patched():
            with encinfo.extra_encodings():
                cls._patched_environment = True
                try:
                    yield
                finally:
                    cls._patched_environment = False
        cls._patched_environment = None

    def __init__(self, path, *, options):
        if self._patched_environment is not True:
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
        except struct.error:
            self.tag('invalid-mo-file')
            return
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
                s = broken_encoding.object
                assert isinstance(s, bytes)
                begin = max(broken_encoding.start - 40, 0)
                end = broken_encoding.start + 40
                s = s[begin:end]
                self.tag('broken-encoding',
                    tags.safestr(repr(s)[1:]),
                    tags.safestr('cannot be decoded as'),
                    broken_encoding.encoding.upper(),
                )
                broken_encoding = True
        # check_headers() modifies the file metadata,
        # so it has to be the first check:
        self.check_headers(file)
        language = self.check_language(file, is_template=is_template)
        self.check_plurals(file, is_template=is_template, language=language)
        encoding = self.check_mime(file, is_template=is_template, language=language)
        if broken_encoding:
            encoding = None
        self.check_dates(file, is_template=is_template)
        self.check_project(file)
        self.check_translator(file, is_template=is_template)
        self.check_messages(file, encoding=encoding)

    def check_language(self, file, *, is_template):
        if is_template:
            if 'Language' in file.metadata.duplicates:
                self.tag('duplicate-header-field-language')
            elif not 'Language' in file.metadata:
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
        if 'Language' in file.metadata.duplicates:
            self.tag('duplicate-header-field-language')
            duplicate_meta_language = True
            meta_language = None
        else:
            duplicate_meta_language = False
            meta_language = file.metadata.get('Language')
        orig_meta_language = meta_language
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
            if meta_language.remove_nonlinguistic_modifier():
                self.tag('language-variant-does-not-affect-translation', orig_meta_language)
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
            if not orig_meta_language and not duplicate_meta_language:
                self.tag('no-language-header-field')
            self.tag('unable-to-determine-language')
            return
        if not orig_meta_language and not duplicate_meta_language:
            self.tag('no-language-header-field', tags.safestr('Language:'), language)
        return language

    def check_plurals(self, file, *, is_template, language):
        if 'Plural-Forms' in file.metadata.duplicates:
            self.tag('duplicate-header-field-plural-forms')
            return
        correct_plural_forms = None
        if language is not None:
            correct_plural_forms = language.get_plural_forms()
        plural_forms = file.metadata.get('Plural-Forms')
        has_plurals = False  # messages with plural forms (translated or not)?
        expected_nplurals = {}  # number of plurals in _translated_ messages
        for message in file:
            if message.obsolete:
                continue
            if message.msgid_plural:
                has_plurals = True
                if isinstance(message, polib.POEntry) and not message.translated():
                    continue
                expected_nplurals[len(message.msgstr_plural)] = message
                if len(expected_nplurals) > 1:
                    break
        if len(expected_nplurals) > 1:
            args = []
            for n, message in sorted(expected_nplurals.items()):
                args += [n, message_repr(message, template='({})'), '!=']
            self.tag('inconsistent-number-of-plural-forms', *args[:-1])
        if is_template:
            plural_forms_hint = 'nplurals=INTEGER; plural=EXPRESSION;'
        elif correct_plural_forms:
            plural_forms_hint = tags.safe_format(
                ' or '.join('{}' for s in correct_plural_forms),
                *correct_plural_forms
            )
        else:
            plural_forms_hint = 'nplurals=<n>; plural=<expression>'
        if plural_forms is None:
            if has_plurals:
                if expected_nplurals:
                    self.tag('no-required-plural-forms-header-field', plural_forms_hint)
                else:
                    self.tag('no-plural-forms-header-field', plural_forms_hint)
            return
        if is_template:
            return
        try:
            (n, expr) = gettext.parse_plural_forms(plural_forms)
        except gettext.PluralFormsSyntaxError:
            if has_plurals:
                self.tag('syntax-error-in-plural-forms', plural_forms, '=>', plural_forms_hint)
            else:
                self.tag('syntax-error-in-unused-plural-forms', plural_forms, '=>', plural_forms_hint)
        else:
            if len(expected_nplurals) == 1:
                [expected_nplurals] = expected_nplurals.keys()
                if n != expected_nplurals:
                    self.tag('incorrect-number-of-plural-forms',
                        n, tags.safestr('(Plural-Forms header field)'), '!=',
                        expected_nplurals, tags.safestr('(number of msgstr items)')
                    )
            locally_correct_n = locally_correct_expr = None
            if correct_plural_forms is not None:
                locally_correct_plural_forms = [
                    (i, expression)
                    for i, expression in map(gettext.parse_plural_forms, correct_plural_forms)
                    if i == n
                ]
                if not locally_correct_plural_forms:
                    if has_plurals:
                        self.tag('incorrect-plural-forms', plural_forms, '=>', plural_forms_hint)
                    else:
                        self.tag('incorrect-unused-plural-forms', plural_forms, '=>', plural_forms_hint)
                elif len(locally_correct_plural_forms) == 1:
                    [[locally_correct_n, locally_correct_expr]] = locally_correct_plural_forms
            try:
                for i in range(200):
                    fi = expr(i)
                    if fi >= n:
                        message = tags.safe_format('f({}) = {} >= {}'.format(i, fi, n))
                        if has_plurals:
                            self.tag('codomain-error-in-plural-forms', message)
                        else:
                            self.tag('codomain-error-in-unused-plural-forms', message)
                        break
                    if n == locally_correct_n and fi != locally_correct_expr(i):
                        if has_plurals:
                            self.tag('incorrect-plural-forms', plural_forms, '=>', plural_forms_hint)
                        else:
                            self.tag('incorrect-unused-plural-forms', plural_forms, '=>', plural_forms_hint)
                        break
            except OverflowError:
                message = tags.safe_format('f({}): integer overflow', i)
                if has_plurals:
                    self.tag('arithmetic-error-in-plural-forms', message)
                else:
                    self.tag('arithmetic-error-in-unused-plural-forms', message)
            except ZeroDivisionError:
                message = tags.safe_format('f({}): division by zero', i)
                if has_plurals:
                    self.tag('arithmetic-error-in-plural-forms', message)
                else:
                    self.tag('arithmetic-error-in-unused-plural-forms', message)
            codomain = expr.codomain()
            if codomain is not None:
                (x, y) = codomain
                if x > 0:
                    rng = range(0, x)
                    rng = misc.format_range(rng, max=5)
                    message = tags.safestr('f(x) != {}'.format(rng))
                    if has_plurals:
                        self.tag('codomain-error-in-plural-forms', message)
                    else:
                        self.tag('codomain-error-in-unused-plural-forms', message)
                if y + 1 < n:
                    rng = range(y + 1, n)
                    rng = misc.format_range(rng, max=5)
                    message = tags.safestr('f(x) != {}'.format(rng))
                    if has_plurals:
                        self.tag('codomain-error-in-plural-forms', message)
                    else:
                        self.tag('codomain-error-in-unused-plural-forms', message)

    def check_mime(self, file, *, is_template, language):
        # MIME-Version:
        mime_version = file.metadata.get('MIME-Version')
        if 'MIME-Version' in file.metadata.duplicates:
            self.tag('duplicate-header-field-mime-version')
        elif mime_version is not None:
            if mime_version != '1.0':
                self.tag('invalid-mime-version', mime_version, '=>', '1.0')
        else:
            self.tag('no-mime-version-header-field', tags.safestr('MIME-Version: 1.0'))
        # Content-Transfer-Encoding:
        cte = file.metadata.get('Content-Transfer-Encoding')
        if 'Content-Transfer-Encoding' in file.metadata.duplicates:
            self.tag('duplicate-header-field-content-transfer-encoding')
        elif cte is not None:
            if cte != '8bit':
                self.tag('invalid-content-transfer-encoding', cte, '=>', '8bit')
        else:
            self.tag('no-content-transfer-encoding-header-field', tags.safestr('Content-Transfer-Encoding: 8bit'))
        # Content-Type:
        if 'Content-Type' in file.metadata.duplicates:
            duplicate_ct = True
            ct = None
        else:
            duplicate_ct = False
            ct = file.metadata.get('Content-Type')
        encoding = None
        content_type_hint = 'text/plain; charset=<encoding>'
        if ct is not None:
            match = re.search(r'(\Atext/plain; )?\bcharset=([^\s;]+)\Z', ct)
            if match:
                encinfo = self.options.encinfo
                encoding = match.group(2)
                try:
                    is_ascii_compatible = encinfo.is_ascii_compatible_encoding(encoding)
                except LookupError:
                    if encoding == 'CHARSET':
                        if not is_template:
                            self.tag('boilerplate-in-content-type', ct)
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
                            encoding = new_encoding
                        else:
                            self.tag('non-portable-encoding', encoding)
                    if language is not None:
                        unrepresentable_characters = language.get_unrepresentable_characters(encoding)
                        if unrepresentable_characters:
                            if len(unrepresentable_characters) > 5:
                                unrepresentable_characters[4:] = ['...']
                            self.tag('unrepresentable-characters', encoding, *unrepresentable_characters)
                if match.group(1) is None:
                    if encoding is not None:
                        content_type_hint = content_type_hint.replace('<encoding>', encoding)
                    self.tag('invalid-content-type', ct, '=>', content_type_hint)
            else:
                self.tag('invalid-content-type', ct, '=>', content_type_hint)
        elif duplicate_ct:
            self.tag('duplicate-header-field-content-type')
        else:
            self.tag('no-content-type-header-field', tags.safestr('Content-Type: ' + content_type_hint))
        return encoding

    def check_dates(self, file, *, is_template):
        for field in 'POT-Creation-Date', 'PO-Revision-Date':
            if field in file.metadata.duplicates:
                self.tag('duplicate-header-field-date', field)
                continue
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
        # Project-Id-Version:
        project_id_version = file.metadata.get('Project-Id-Version')
        if 'Project-Id-Version' in file.metadata.duplicates:
            self.tag('duplicate-header-field-project-id-version')
        if project_id_version is None:
            self.tag('no-project-id-version-header-field')
        elif project_id_version in {'PACKAGE VERSION', 'PROJECT VERSION'}:
            self.tag('boilerplate-in-project-id-version', project_id_version)
        else:
            if not re.search(r'[A-Za-z]', project_id_version):
                self.tag('no-package-name-in-project-id-version', project_id_version)
            if not re.search(r'[0-9]', project_id_version):
                self.tag('no-version-in-project-id-version', project_id_version)
        # Report-Msgid-Bugs-To:
        report_msgid_bugs_to = file.metadata.get('Report-Msgid-Bugs-To')
        if 'Report-Msgid-Bugs-To' in file.metadata.duplicates:
            self.tag('duplicate-header-field-report-msgid-bugs-to')
        elif not report_msgid_bugs_to:
            self.tag('no-report-msgid-bugs-to-header-field')
        elif report_msgid_bugs_to:
            real_name, email_address = email.utils.parseaddr(report_msgid_bugs_to)
            if '@' not in email_address:
                uri = urllib.parse.urlparse(report_msgid_bugs_to)
                if uri.scheme == '':
                    self.tag('invalid-report-msgid-bugs-to', report_msgid_bugs_to)
            elif rfc2606.is_reserved_email(email_address):
                self.tag('invalid-report-msgid-bugs-to', report_msgid_bugs_to)
            elif email_address == 'EMAIL@ADDRESS':
                self.tag('boilerplate-in-report-msgid-bugs-to', report_msgid_bugs_to)

    def check_translator(self, file, *, is_template):
        # Last-Translator:
        translator = file.metadata.get('Last-Translator')
        if 'Last-Translator' in file.metadata.duplicates:
            self.tag('duplicate-header-field-last-translator')
        elif translator is None:
            self.tag('no-last-translator-header-field')
        else:
            translator_name, translator_email = email.utils.parseaddr(translator)
            if '@' not in translator_email:
                self.tag('invalid-last-translator', translator)
            elif rfc2606.is_reserved_email(translator_email):
                self.tag('invalid-last-translator', translator)
            elif translator_email == 'EMAIL@ADDRESS':
                if not is_template:
                    self.tag('boilerplate-in-last-translator', translator)
        # Language-Team:
        team = file.metadata.get('Language-Team')
        if 'Language-Team' in file.metadata.duplicates:
            self.tag('duplicate-header-field-language-team')
        elif team is None:
            self.tag('no-language-team-header-field')
        else:
            team_name, team_email = email.utils.parseaddr(team)
            if '@' not in team_email:
                # TODO: An URL is also allowed here.
                # self.tag('invalid-language-team', translator)
                pass
            elif rfc2606.is_reserved_email(team_email):
                self.tag('invalid-language-team', team)
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
        header_fields = frozenset(self.options.gettextinfo.header_fields)
        header_fields_lc = {str.lower(s): s for s in header_fields}
        class userdict(dict): pass
        new_metadata = userdict()
        seen_conflict_marker = False
        for key, value in sorted(file.metadata.items()):
            if not gettext.is_valid_field_name(key):
                self.tag('stray-header-line', key + ':')
                continue
            value, *strays = value.split('\n')
            for stray in strays:
                if gettext.search_for_conflict_marker(stray):
                    if not seen_conflict_marker:
                        self.tag('conflict-marker-in-header', stray)
                        seen_conflict_marker = True
                else:
                    self.tag('stray-header-line', stray)
            new_metadata[key] = value
            if key.startswith('X-'):
                continue
            if key not in header_fields:
                hint = header_fields_lc.get(key.lower())
                if hint is None:
                    hints = difflib.get_close_matches(key, header_fields, n=1, cutoff=0.8)
                    if hints:
                        [hint] = hints
                if hint in file.metadata:
                    hint = None
                if hint is None:
                    self.tag('unknown-header-field', key)
                else:
                    self.tag('unknown-header-field', key, '=>', hint)
        try:
            duplicates = file.metadata.duplicates
        except AttributeError:
            duplicates = {}
        else:
            for key, values in sorted(duplicates.items()):
                if not gettext.is_valid_field_name(key):
                    self.tag('stray-header-line', key + ':')
                elif key in {
                    'Content-Transfer-Encoding',
                    'Content-Type',
                    'Language',
                    'Language-Team',
                    'Last-Translator',
                    'MIME-Version',
                    'PO-Revision-Date',
                    'POT-Creation-Date',
                    'Plural-Forms',
                    'Project-Id-Version',
                    'Report-Msgid-Bugs-To'
                }:
                    # These will be handled elsewhere.
                    pass
                else:
                    self.tag('duplicate-header-field', key)
                for value in values:
                    value, *strays = value.split('\n')
                    for stray in strays:
                        self.tag('stray-header-line', stray)
        new_metadata.duplicates = frozenset(duplicates)
        file.metadata = new_metadata

    def check_messages(self, file, *, encoding):
        if encoding is None:
            return
        encinfo = self.options.encinfo
        found_unusual_characters = set()
        msgid_counter = collections.Counter()
        if len(file) == 0:
            self.tag('empty-file')
        for message in file:
            if message.obsolete:
                continue
            fuzzy = isinstance(message, polib.POEntry) and 'fuzzy' in message.flags
            leading_lf = message.msgid.startswith('\n')
            trailing_lf = message.msgid.endswith('\n')
            strings = [message.msgid_plural]
            if not fuzzy:
                strings += [message.msgstr]
                strings += message.msgstr_plural.values()
            strings = [s for s in strings if s != '']
            for s in strings:
                if s.startswith('\n') != leading_lf:
                    self.tag('inconsistent-leading-newlines', message_repr(message))
                    break
            for s in strings:
                if s.endswith('\n') != trailing_lf:
                    self.tag('inconsistent-trailing-newlines', message_repr(message))
                    break
            msgid_uc = (
                set(find_unusual_characters(message.msgid)) |
                set(find_unusual_characters(message.msgid_plural))
            )
            strings = [message.msgstr] + sorted(message.msgstr_plural.values())

            conflict_marker = None
            for msgstr in strings:
                msgstr_uc = set(find_unusual_characters(msgstr))
                uc = msgstr_uc - msgid_uc - found_unusual_characters
                if uc:
                    names = ', '.join(
                        'U+{:04X} {}'.format(ord(ch), encinfo.get_character_name(ch))
                        for ch in sorted(uc)
                    )
                    self.tag('unusual-character-in-translation', tags.safestr(names + ':'), msgstr)
                    found_unusual_characters |= uc
                if conflict_marker is None:
                    conflict_marker = gettext.search_for_conflict_marker(msgstr)
                    if conflict_marker is not None:
                        conflict_marker = conflict_marker.group(0)
                        self.tag('conflict-marker-in-translation', message_repr(message), conflict_marker)
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

# vim:ts=4 sw=4 et
