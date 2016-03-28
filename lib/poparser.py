# Copyright © 2016 Jakub Wilk <jwilk@jwilk.net>
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

'''
PO file parser
'''

import re

import rply
import rply.errors
import rply.token

from lib import misc

class SyntaxError(Exception):
    pass

Token = rply.token.Token
SourcePosition = rply.token.SourcePosition

# PO file format documentation:
# * https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html

def _lexer_regex():
    regex_list = []
    token_types = set()
    def add(**kwargs):
        [(tname, regex)] = kwargs.items()
        if regex is not None:
            regex_list.append(
                '(?P<{tok}>{re})'.format(tok=tname, re=regex)
            )
        if tname[0] != '_':
            token_types.add(tname.upper())
    add(_WS=r'[ \t\r\f\v]+')
    add(_NL=r'\n')
    add(_OBSOLETE_PREV='#~[|]')
    add(OBSOLETE='#~')
    add(UNOBSOLETE=None)
    add(PREV='#[|]')
    add(UNPREV=None)
    add(COMMENT='#.*')
    add(DOMAIN='domain')
    add(MSGID_PLURAL='msgid_plural')
    add(MSGID='msgid')
    add(MSGSTR='msgstr')
    add(MSGCTXT='msgctxt')
    add(INDEX='[[]')
    add(UNINDEX='[]]')
    add(NUMBER='[0-9]+')
    add(STRING=r'"(?:[^"\n\\]|\\.)*"')
    return (
        re.compile('|'.join(regex_list)),
        frozenset(token_types)
    )

def _token_from_match(match, pos):
    for tname, s in match.groupdict().items():
        if s is None:
            continue
        tname = tname.upper()
        return Token(tname, s, pos)
    else:
        assert False

class LexingError(Exception):

    def __init__(self, reason, pos):
        self.reason = reason
        self.pos = pos

class Lexer(object):

    (regex, token_types) = _lexer_regex()

    def __init__(self, file, *, encoding='ASCII'):
        self.file = file
        self.encoding = encoding

    def __iter__(self):
        prev = False
        obsolete = False
        pending_unprev = False
        pending_unobsolete = False
        for lineno, line in enumerate(self.file):
            assert isinstance(line, bytes)
            try:
                line = line.decode(self.encoding)
            except UnicodeDecodeError as exc:
                pos = SourcePosition(None, lineno, None)
                raise LexingError(exc, pos)
            colno = 0
            for match in self.regex.finditer(line):
                pos = SourcePosition(None, lineno, colno)
                if match.start() != colno:
                    raise LexingError(None, pos)
                colno = match.end()
                token = _token_from_match(match, pos)
                if token.name == '_NL':
                    pending_unprev = prev
                    pending_unobsolete = obsolete
                    continue
                if token.name == '_WS':
                    continue
                if token.name == '_OBSOLETE_PREV':
                    obsolete = True
                    prev = True
                    if pending_unobsolete:
                        pending_unobsolete = False
                    else:
                        yield Token('OBSOLETE', '', pos)
                    if pending_unprev:
                        pending_unprev = False
                    else:
                        yield Token('PREV', '', pos)
                    continue
                elif token.name == 'OBSOLETE':
                    obsolete = True
                    if pending_unobsolete:
                        pending_unobsolete = False
                        continue
                elif token.name == 'PREV':
                    prev = True
                    if pending_unprev:
                        pending_unprev = False
                        continue
                if pending_unprev:
                    yield Token('UNPREV', '', pos)
                    prev = False
                    pending_unprev = False
                if pending_unobsolete:
                    yield Token('UNOBSOLETE', '', pos)
                    obsolete = False
                    pending_unobsolete = False
                yield token
            if colno != len(line):
                pos = SourcePosition(None, lineno, colno)
                raise LexingError(None, pos)


class File(object):

    def __init__(self):
        self._domain = None
        self._unused_domain = None
        self._comments = None
        self.entries = []

    def warn(self, *args, **kwargs):
        # TODO
        pass

class Entry(object):

    def __init__(self, *, domain=None, msgctxt=None, msgid=None, msgid_plural=None, msgstr=None, msgstr_plural=None):
        self.domain = domain
        self.msgctxt = msgctxt
        self.msgid = msgid
        self.msgid_plural = msgid_plural
        self.msgstr = msgstr
        self.msgstr_plural = msgstr_plural

def create_parser():
    pg = rply.ParserGenerator(
        Lexer.token_types,
        precedence=[
            ('nonassoc', ['file']),
            ('nonassoc', ['COMMENT']),
        ],
        cache_id='i18nspector-po'
    )
    @pg.production('start : file')
    def start(p):
        [file] = p
        if file._comments:
            file.warn('trailing comments', file._comments)
            file._comments = None
        return file
    # file:
    @pg.production('file :')
    def file_comments(p):
        file = File()
        return file
    @pg.production('file : file comments', precedence='file')
    def file_comments(p):
        [file, comments] = p
        assert file._comments is None
        file._comments = comments
        return file
    @pg.production('file : file domain')
    def file_domain(p):
        # FIXME
        [file, domain, comments] = p
        if file._unused_domain:
            file.warn('unused domain', self._domain)
        file._domain = p[1]
        file._unused_domain = True
        if file._comments:
            file.warn('domain comments', self._comments)
            file._comments = None
        return file
    @pg.production('file : file entry')
    def file_entry(p):
        [file, entry] = p
        file.entries += [entry]
        entry.comments = file._comments
        file._comments = None
        return file
    @pg.production('file : file OBSOLETE entries UNOBSOLETE')
    def file_obs_entries(p):
        [file, entries, comments] = p
        file.entries += entries
        for entry in entries:
            entry.obsolete = True
        entries[0].comments = file._comments
        file._comments = None
        return file
    # comments:
    @pg.production('comments : COMMENT')
    def comments_single(p):
        [comment] = p
        return [comment]
    @pg.production('comments : comments COMMENT')
    def comments_multi(p):
        [comments, comment] = p
        comments += [comment]
        return comments
    # domain:
    @pg.production('domain : DOMAIN STRING')
    def msgid(p):
        [_, s] = p
        return s
    # entries:
    @pg.production('entries : entry')
    def entries_single(p):
        [entry] = p
        return [entry]
    @pg.production('entries : entries entry')
    def entries_multi(p):
        [entries, entry] = p
        entries += [entry]
        return entries
    # entry:
    @pg.production('entry : bare-entry-sng')
    def entry_singular(p):
        [entry] = p
        assert isinstance(entry, Entry)
        return entry
    @pg.production('entry : prev-sng bare-entry-sng')
    def entry_singular_prev(p):
        [(prev_ctxt, prev_msgid), entry] = p
        entry.prev_ctxt = prev_ctxt
        entry.prev_msgid = prev_msgid
        assert isinstance(entry, Entry)
        return entry
    @pg.production('entry : bare-entry-plural')
    def entry_plural(p):
        [entry] = p
        assert isinstance(entry, Entry)
        return entry
    @pg.production('entry : prev-plural bare-entry-plural')
    def entry_plural_prev(p):
        [(prev_ctxt, prev_msgid, prev_msgid_plural), entry] = p
        entry.prev_ctxt = prev_ctxt
        entry.prev_msgid = prev_msgid
        entry.prev_msgid_plural = prev_msgid_plural
        assert isinstance(entry, Entry)
        return entry
    # bare-entry-sng:
    @pg.production('bare-entry-sng : msgid msgstr')
    def bare_entry_singular(p):
        [msgid, msgstr] = p
        return Entry(
            msgid=msgid,
            msgstr=msgstr,
        )
    @pg.production('bare-entry-sng : msgctxt msgid msgstr')
    def bare_entry_singular_ctxt(p):
        [msgctxt, msgid, msgstr] = p
        return Entry(
            msgctxt=msgctxt,
            msgid=msgid,
            msgstr=msgstr,
        )
    # bare-entry-plural:
    @pg.production('bare-entry-plural : msgid msgid-plural msgstr-plural')
    def bare_entry_plural(p):
        [msgid, msgid_plural, msgstr_plural] = p
        return Entry(
            msgid=msgid,
            msgid_plural=msgid_plural,
            msgstr_plural=msgstr_plural,
        )
    @pg.production('bare-entry-plural : msgctxt msgid msgid-plural msgstr-plural')
    def bare_entry_plural_ctxt(p):
        [msgctxt, msgid, msgid_plural, msgstr_plural] = p
        return Entry(
            msgctxt=msgctxt,
            msgid=msgid,
            msgid_plural=msgid_plural,
            msgstr_plural=msgstr_plural,
        )
    # msgctxt, msgid, msgid-plural, msgstr:
    @pg.production('msgctxt : MSGCTXT string-list')
    @pg.production('msgid : MSGID string-list')
    @pg.production('msgid-plural : MSGID_PLURAL string-list')
    @pg.production('msgstr : MSGSTR string-list')
    def msgid(p):
        [_, slist] = p
        return ''.join(s.getstr() for s in slist)
    # msgstr-plural:
    @pg.production('msgstr-plural : msgstr-n')
    def msgstr_pl_single(p):
        [item] = p
        return [item]
    @pg.production('msgstr-plural : msgstr-plural msgstr-n')
    def msgstr_pl_multi(p):
        [items, item] = p
        items += [item]
        return items
    # msgstr-n:
    @pg.production('msgstr-n : MSGSTR INDEX NUMBER UNINDEX string-list')
    def msgstr_n(p):
        [_, _, n, _, slist] = p
        s = ''.join(s.getstr() for s in slist)
        return (n, s)
    # string-list:
    @pg.production('string-list : STRING')
    def string_list_single(p):
        [s] = p
        return [s]
    @pg.production('string-list : string-list STRING')
    def string_list_multi(p):
        [slist, s] = p
        slist += [s]
        return slist
    # prev-sng:
    @pg.production('prev-sng : PREV msgid UNPREV')
    def prev_sng(p):
        [_, msgid, _] = p
        return (None, msgid)
    @pg.production('prev-sng : PREV msgctxt msgid UNPREV')
    def prev_sng_ctxt(p):
        [_, msgctxt, msgid, _] = p
        return (msgctxt, msgid)
    # prev-plural:
    @pg.production('prev-plural : PREV msgid msgid-plural UNPREV')
    def prev_plural_ctxt(p):
        [_, msgid, msgid_plural, _] = p
        return (None, msgid, msgid_pulral)
    @pg.production('prev-plural : PREV msgctxt msgid msgid-plural UNPREV')
    def prev_plural(p):
        [_, msgctxt, msgid, msgid_plural, _] = p
        return (msgctxt, msgid, msgid_plural)
    # -----------------------------------------
    with misc.throwaway_tempdir('rply'):
        # Use private temporary directory
        # to mitigate RPLY's insecure use of /tmp:
        # CVE-2014-1604, CVE-2014-1938
        return pg.build()

parser = create_parser()

def main():
    import argparse
    ap = argparse.ArgumentParser(description='msgcat(1) replacement')
    ap.add_argument('files', metavar='<file>', nargs='+')
    options = ap.parse_args()
    for path in options.files:
        escaped_path = ascii(path)[1:-1]
        print('# ' + escaped_path, end='\n\n')
        with open(path, 'rb') as file:
            lexer = Lexer(file, encoding='ISO-8859-1')
            try:
                x = parser.parse(iter(lexer))
            except ParsingError as exc:
                print(exc)
            else:
                print(x)

def parse(path, *, encoding='ISO-8859-1'):
    with open(path, 'rb') as file:
        lexer = Lexer(file, encoding='ISO-8859-1')
        try:
            return parser.parse(iter(lexer))
        except (rply.errors.LexingError, rply.errors.ParsingError) as exc:
            raise SyntaxError(exc)

if __name__ == '__main__':
    main()
else:
    del main

__all__ = ['parse', 'SyntaxError']

# vim:ts=4 sts=4 sw=4 et
