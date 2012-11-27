#!/usr/bin/python3

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

import datetime
import functools
import os
import re

from lib import misc

class GettextInfo(object):

    def __init__(self, datadir):
        path = os.path.join(datadir, 'po-header-fields')
        with open(path, 'rt', encoding='ASCII') as file:
            fields = [
                s.rstrip() for s in file
                if s.rstrip() and not s.startswith('#')
            ]
        misc.check_sorted(fields)
        self.po_header_fields = frozenset(fields)

# ================
# Plurals handling
# ================

class PluralFormsSyntaxError(Exception):
    pass

class PluralExpressionSyntaxError(PluralFormsSyntaxError):
    pass

_plural_exp_tokens = [
    (r'[0-9]+', None),
    (r'[=!]=', None),
    (r'!', 'not'),
    (r'&&', 'and'),
    (r'[|][|]', 'or'),
    (r'[<>]=?', None),
    (r'[*/%]', None),
    (r'[+-]', None),
    (r'n', None),
    (r'[?:]', None),
    (r'[()]', None),
    (r'[ \t]', None),
    (r'.', '_'), # junk
]

_plural_exp_token_re = '|'.join(
    chunk if repl is None else '(?P<{}>{})'.format(repl, chunk)
    for chunk, repl in _plural_exp_tokens
)
_plural_exp_token_re = re.compile(_plural_exp_token_re)

def _plural_exp_tokenize(s):
    for match in _plural_exp_token_re.finditer(s):
        for pytoken, ctoken in match.groupdict().items():
            if ctoken is not None:
                break
        if ctoken is not None:
            if pytoken == '_': # junk
                raise PluralExpressionSyntaxError(match.group(0))
            yield ' {} '.format(pytoken)
        else:
            yield match.group(0)

_ifelse_re = re.compile(r'(.*?)[?](.*?):(.*)')
def _subst_ifelse(match):
    return '({true} if {cond} else {false})'.format(
        cond=match.group(1),
        true=match.group(2),
        false=_subst_ifelse(match.group(3))
    )
# The magic below makes _subst_ifelse() act on strings rather than match
# objects.
_subst_ifelse = functools.partial(_ifelse_re.sub, _subst_ifelse)

def parse_plural_expression(s):
    stack = ['']
    for token in _plural_exp_tokenize(s):
        if token == '(':
            stack += ['']
        elif token == ')':
            if len(stack) <= 1:
                raise PluralExpressionSyntaxError
            s = _subst_ifelse(stack.pop())
            stack[-1] += '({})'.format(s)
        else:
            stack[-1] += token
    if len(stack) != 1:
        raise PluralExpressionSyntaxError
    [s] = stack
    s = _subst_ifelse(s)
    try:
        fn = eval('lambda n: int({})'.format(s))
    except SyntaxError as exc:
        assert 0, "{!r} couldn't be parsed as Python expression".format(s)
        raise PluralExpressionSyntaxError
    fn.__name__ = 'plural'
    return fn

_parse_plural_forms = re.compile(r'^\s*nplurals=([1-9][0-9]*);\s*plural=([^;]+);?\s*$').match

def parse_plural_forms(s):
    match = _parse_plural_forms(s)
    if match is None:
        raise PluralFormsSyntaxError
    n = int(match.group(1), 10)
    expr = parse_plural_expression(match.group(2))
    return (n, expr)

# =====
# Dates
# =====

class DateSyntaxError(Exception):
    pass

_parse_date = re.compile('''
    ^ \s*
    ( [0-9]{4}-[0-9]{2}-[0-9]{2} ) # YYYY-MM-DD
    ( \s+ )
    ( [0-9]{2}:[0-9]{2} ) # hh:mm
    (?: : [0-9]{2} )? # ss
    \s*
    ( [+-] [0-9]{2} ) # ZZ
    :?
    ( [0-9]{2} ) # zz
    \s* $
''', re.VERBOSE).match

def fix_date_format(s):
    match = _parse_date(s)
    if match is None:
        return
    s = ''.join(g if not g.isspace() else ' ' for g in match.groups())
    assert len(s) == 21, 'len({!r}) != 21'.format(s)
    try:
        parse_date(s)
    except DateSyntaxError:
        return
    return s

def parse_date(s):
    try:
        return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M%z')
    except ValueError as exc:
        raise DateSyntaxError(exc)

epoch = datetime.datetime(1995, 7, 2, tzinfo=datetime.timezone.utc)

# vim:ts=4 sw=4 et
