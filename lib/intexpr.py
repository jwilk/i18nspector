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

'''
squeeze Python abstract syntax trees into C integer expressions semantics
'''

import ast

class Evaluator(object):

    def __init__(self, node, n, *, precision):
        class context: pass
        context.n = n
        context.max = 1 << precision
        self._ctxt = context
        self._node = node
        self._check_overflow(n)

    def __call__(self):
        node = self._node
        assert isinstance(node, ast.Expr)
        return self._visit_expr(node)

    def _check_overflow(self, n):
        if n < 0:
            raise OverflowError(n)
        if n >= self._ctxt.max:
            raise OverflowError(n)
        return n

    def _visit(self, node, *args):
        try:
            fn = getattr(self, '_visit_' + type(node).__name__.lower())
        except KeyError:
            raise NotImplementedError(type(node).__name__)
        return fn(node, *args)

    def _visit_expr(self, node):
        [node] = ast.iter_child_nodes(node)
        return self._visit(node)

    # binary operators
    # ================

    def _visit_binop(self, node):
        x = self._visit(node.left)
        y = self._visit(node.right)
        return self._visit(node.op, x, y)

    def _visit_add(self, node, x, y):
        return self._check_overflow(x + y)

    def _visit_sub(self, node, x, y):
        return self._check_overflow(x - y)

    def _visit_mult(self, node, x, y):
        return self._check_overflow(x * y)

    def _visit_div(self, node, x, y):
        return x // y

    def _visit_mod(self, node, x, y):
        return x % y

    # unary operators
    # ===============

    def _visit_unaryop(self, node):
        x = self._visit(node.operand)
        return self._visit(node.op, x)

    def _visit_not(self, node, x):
        return int(not x)

    def _visit_usub(self, node, x):
        return self._check_overflow(-x)

    def _visit_uadd(self, node, x):
        return x

    # comparison operators
    # ====================

    def _visit_compare(self, node):
        # This one is tricky because in C equality comparison operators have
        # lower priority that inequality comparison operators. This is unlike
        # Python, in which they have the same priority.
        assert len(node.comparators) == len(node.ops)
        new_vals = []
        new_ops = []
        # high priority: <, <=, >, >=
        left = self._visit(node.left)
        for op, right in zip(node.ops, node.comparators):
            right = self._visit(right)
            if isinstance(op, (ast.Eq, ast.NotEq)):
                new_vals += [left]
                new_ops += [op]
                left = right
            else:
                left = self._visit(op, left, right)
        new_vals += [left]
        assert len(new_vals) == len(new_ops) + 1
        # low priority: ==, !=
        new_vals = iter(new_vals)
        left = next(new_vals)
        for op, right in zip(new_ops, new_vals):
            left = self._visit(op, left, right)
        return left

    def _visit_gte(self, node, x, y):
        return int(x >= y)

    def _visit_gt(self, node, x, y):
        return int(x > y)

    def _visit_lte(self, node, x, y):
        return int(x <= y)

    def _visit_lt(self, node, x, y):
        return int(x < y)

    def _visit_eq(self, node, x, y):
        return int(x == y)

    def _visit_noteq(self, node, x, y):
        return int(x != y)

    # boolean operators
    # =================

    def _visit_boolop(self, node):
        return self._visit(node.op, *node.values)

    def _visit_and(self, node, *args):
        for arg in args:
            if self._visit(arg) == 0:
                return 0
        return 1

    def _visit_or(self, node, *args):
        for arg in args:
            if self._visit(arg) != 0:
                return 1
        return 0

    # if-then-else expression
    # =======================

    def _visit_ifexp(self, node):
        test = self._visit(node.test)
        if test:
            return self._visit(node.body)
        else:
            return self._visit(node.orelse)

    # contants, variables
    # ===================

    def _visit_num(self, node):
        return self._check_overflow(node.n)

    def _visit_name(self, node):
        return self._ctxt.n

class Expression(object):

    def __init__(self, s):
        module = ast.parse('({})'.format(s), filename='<intexpr>')
        assert isinstance(module, ast.Module)
        [node] = ast.iter_child_nodes(module)
        if not isinstance(node, ast.Expr):
            raise TypeError
        self._node = node

    def __call__(self, n, *, precision=32):
        '''
        return f(n)
        '''
        e = Evaluator(self._node, n, precision=precision)
        return e()

# vim:ts=4 sw=4 et
