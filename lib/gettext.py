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

import functools
import os
import re

from lib import misc

class GettextInfo(object):

    def __init__(self, datadir):
        path = os.path.join(datadir, 'po-header-fields')
        with open(path, 'rt', encoding='ASCII') as file:
            fields = [s.rstrip() for s in file]
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
    (r'\s+', None),
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
    fn = eval('lambda n: int({})'.format(s))
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

# vim:ts=4 sw=4 et
