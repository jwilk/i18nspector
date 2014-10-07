# Copyright © 2012, 2013, 2014 Jakub Wilk <jwilk@jwilk.net>
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

import ast
import inspect

import lib.tags as M
import lib.checker

from nose.tools import (
    assert_equal,
    assert_is_instance,
)

class test_escape:

    def t(self, s, expected):
        result = M.safe_format('{}', s)
        assert_is_instance(result, M.safestr)
        assert_equal(
            result,
            expected
        )

    def test_safe(self):
        s = 'fox'
        self.t(s, s)

    def test_trailing_newline(self):
        s = 'fox\n'
        self.t(s, repr(s))

    def test_colon(self):
        s = 'fox:'
        self.t(s, repr(s))

    def test_space(self):
        s = 'brown fox'
        self.t(s, repr(s))

def ast_to_tagnames(node):
    for child in ast.iter_child_nodes(node):
        for t in ast_to_tagnames(child):
            yield t
    ok = (
        isinstance(node, ast.Call) and
        isinstance(node.func, ast.Attribute) and
        node.func.attr == 'tag' and
        node.args and
        isinstance(node.args[0], ast.Str)
    )
    if ok:
        yield node.args[0].s

def test_consistency():
    source_path = inspect.getsourcefile(lib.checker)
    with open(source_path, 'rt', encoding='UTF-8') as file:
        source = file.read()
        node = ast.parse(source, filename=source_path)
        source_tagnames = frozenset(ast_to_tagnames(node))
    tagnames = frozenset(tag.name for tag in M.iter_tags())
    def test(tag):
        if tag not in source_tagnames:
            raise AssertionError('tag never emitted: ' + tag)
        if tag not in tagnames:
            raise AssertionError(
                'tag missing in data/tags:\n\n'
                '[{tag}]\n'
                'severity = wishlist\n'
                'certainty = wild-guess\n'
                'description = TODO'.format(tag=tag)
            )
    for tag in sorted(source_tagnames | tagnames):
        yield test, tag

# vim:ts=4 sts=4 sw=4 et
