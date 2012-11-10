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

import email.utils
import os
import re
import urllib.parse

import polib

from lib import dates
from lib import gettext
from lib import ling
from lib import misc
from lib import tags

class EnvironmentNotPatched(RuntimeError):
    pass

class Checker(object):

    _patched_environment = False

    @classmethod
    def patch_environment(cls, encinfo):
        # Install extra encoding aliases, that are not known to Python, but
        # occur in real-world PO/MO files:
        encinfo.install_extra_aliases()
        # Do not allow broken/missing encoding declarations, unless the file is
        # ASCII-only:
        polib.default_encoding = 'ASCII'
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
                # FIXME: Because of http://bugs.debian.org/692283, using
                # ISO-8859-1 can trigger spurious syntax errors. A custom
                # encoding that can never produce U+0085 NEXT LINE would be
                # more robust.
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
                language.fix_codes()
                language.remove_encoding()
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
        if plural_forms is None:
            # TODO: Check if it's needed.
            return
        if is_template:
            # TODO: Check if it's needed.
            return
        try:
            (n, expr) = gettext.parse_plural_forms(plural_forms)
        except gettext.PluralFormsSyntaxError:
            self.tag('syntax-error-in-plural-forms', plural_forms, '=>', correct_plural_forms or 'nplurals=<n>; plural=<expression>')

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
                encoding = match.group(1)
                try:
                    ''.encode(encoding)
                except LookupError:
                    if is_template and (encoding == 'CHARSET'):
                        pass
                    else:
                        self.tag('unknown-encoding', encoding)
                    encoding = None
                else:
                    encinfo = self.options.encinfo
                    if encinfo.is_portable_encoding(encoding):
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
            fixed_date = dates.fix_date_format(date)
            if fixed_date is None:
                self.tag('invalid-date', tags.safestr(field + ':'), date)
                continue
            elif date != fixed_date:
                self.tag('invalid-date', tags.safestr(field + ':'), date, '=>', fixed_date)
            stamp = dates.parse_date(fixed_date)
            if stamp > dates.now:
                self.tag('date-from-future', tags.safestr(field + ':'), date)
            if stamp < dates.gettext_epoch:
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

    def check_headers(self, file):
        for key in sorted(file.metadata):
            if key.startswith('X-'):
                continue
            if key not in self.options.gettextinfo.po_header_fields:
                self.tag('unknown-header-field', key)

    def check_messages(self, file, *, encoding):
        if encoding is None:
            return
        has_c1 = re.compile(r'[\x80-\x9f]').search
        for message in file:
            if has_c1(message.msgstr):
                self.tag('c1-control-characters')
                break

# vim:ts=4 sw=4 et
