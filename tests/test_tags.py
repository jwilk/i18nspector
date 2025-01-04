# Copyright © 2012-2022 Jakub Wilk <jwilk@jwilk.net>
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
import importlib
import inspect
import operator
import pkgutil

import lib.check
import lib.tags as M

from .tools import (
    assert_equal,
    assert_false,
    assert_is_instance,
    assert_raises,
    assert_true,
    collect_yielded,
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
        yield from ast_to_tagnames(child)
    ok = (
        isinstance(node, ast.Call) and
        isinstance(node.func, ast.Attribute) and
        node.func.attr == 'tag' and
        node.args
    )
    if ok:
        try:
            value = ast.literal_eval(node.args[0])
        except ValueError:
            return
        yield value

@collect_yielded
def test_consistency():
    source_tagnames = set()
    def visit_mod(modname):
        module = importlib.import_module(modname)
        source_path = inspect.getsourcefile(module)
        with open(source_path, 'rt', encoding='UTF-8') as file:
            source = file.read()
            node = ast.parse(source, filename=source_path)
            source_tagnames.update(ast_to_tagnames(node))
    visit_mod('lib.check')
    for _, modname, _ in pkgutil.walk_packages(lib.check.__path__, 'lib.check.'):
        visit_mod(modname)
    tagnames = frozenset(tag.name for tag in M.iter_tags())
    def test(tag):
        if tag not in source_tagnames:
            raise AssertionError('tag never emitted: ' + tag)
        if tag not in tagnames:
            raise AssertionError(
                'tag missing in data/tags:\n\n'
                f'[{tag}]\n'
                'severity = wishlist\n'
                'certainty = wild-guess\n'
                'description = TODO'
            )
    for tag in sorted(source_tagnames | tagnames):
        yield test, tag

class test_enums:

    def t(self, group, *keys):
        keys = [group[k] for k in keys]
        operators = (
            operator.lt,
            operator.le,
            operator.eq,
            operator.ge,
            operator.gt,
            operator.ne,
        )
        for op in operators:
            for i, x in enumerate(keys):
                for j, y in enumerate(keys):
                    assert_equal(op(x, y), op(i, j))
                    if op is operator.eq:
                        assert_false(op(x, j))
                    elif op is operator.ne:
                        assert_true(op(x, j))
                    else:
                        with assert_raises(TypeError):
                            op(x, j)

    def test_severities(self):
        self.t(M.severities,
            'pedantic',
            'wishlist',
            'minor',
            'normal',
            'important',
            'serious',
        )

    def test_certainties(self):
        self.t(M.certainties,
            'wild-guess',
            'possible',
            'certain',
        )

# vim:ts=4 sts=4 sw=4 et
