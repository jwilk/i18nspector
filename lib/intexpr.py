# Copyright © 2012-2014 Jakub Wilk <jwilk@jwilk.net>
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

from lib import misc

class BaseEvaluator(object):

    def __init__(self, node):
        self._ctxt = misc.Namespace()
        self._node = node

    def __call__(self):
        node = self._node
        assert isinstance(node, ast.Expr)
        return self._visit_expr(node)

    def _visit(self, node, *args):
        try:
            fn = getattr(self, '_visit_' + type(node).__name__.lower())
        except KeyError:  # <no-coverage>
            raise NotImplementedError(type(node).__name__)
        return fn(node, *args)

    def _visit_expr(self, node):
        [node] = ast.iter_child_nodes(node)
        return self._visit(node)

    # binary operators
    # ================

    def _visit_binop(self, node):
        x = self._visit(node.left)
        if x is None:
            return
        y = self._visit(node.right)
        if y is None:
            return
        return self._visit(node.op, x, y)

    # unary operators
    # ===============

    def _visit_unaryop(self, node):
        x = self._visit(node.operand)
        if x is None:
            return
        return self._visit(node.op, x)

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
        if left is None:
            return
        for op, right in zip(node.ops, node.comparators):
            right = self._visit(right)
            if right is None:
                return
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

    # boolean operators
    # =================

    def _visit_boolop(self, node):
        return self._visit(node.op, *node.values)

class Evaluator(BaseEvaluator):

    def __init__(self, node, n, *, bits):
        super().__init__(node)
        self._ctxt.n = n
        self._ctxt.max = 1 << bits

    def _check_overflow(self, n):
        if n < 0:
            raise OverflowError(n)
        if n >= self._ctxt.max:
            raise OverflowError(n)
        return n

    # binary operators
    # ================

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

    def _visit_invert(self, node, x):
        return int(not x)

    # comparison operators
    # ====================

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
        return self._check_overflow(self._ctxt.n)

class CodomainEvaluator(BaseEvaluator):

    def __init__(self, node, *, bits):
        context = misc.Namespace()
        context.max = 1 << bits
        self._ctxt = context
        self._node = node

    def __call__(self):
        node = self._node
        assert isinstance(node, ast.Expr)
        return self._visit_expr(node)

    def _visit(self, node, *args):
        try:
            fn = getattr(self, '_visit_' + type(node).__name__.lower())
        except KeyError:  # <no-coverage>
            raise NotImplementedError(type(node).__name__)
        return fn(node, *args)

    def _visit_expr(self, node):
        [node] = ast.iter_child_nodes(node)
        return self._visit(node)

    # binary operators
    # ================

    def _visit_add(self, node, x, y):
        z = (
            x[0] + y[0],
            min(x[1] + y[1], self._ctxt.max - 1)
        )
        if z[0] > z[1]:
            return
        return z

    def _visit_sub(self, node, x, y):
        z = (
            max(x[0] - y[1], 0),
            x[1] - y[0]
        )
        if z[0] > z[1]:
            return
        return z

    def _visit_mult(self, node, x, y):
        z = (
            x[0] * y[0],
            min(x[1] * y[1], self._ctxt.max - 1)
        )
        if z[0] > z[1]:
            return
        return z

    def _visit_div(self, node, x, y):
        if y == (0, 0):
            # division by zero
            return
        assert y[1] > 0
        return (
            x[0] // y[1],
            x[1] // max(y[0], 1),
        )

    def _visit_mod(self, node, x, y):
        if y == (0, 0):
            # division by zero
            return
        assert y[1] > 0
        if x[1] < y[0]:
            # i % j == i  if  i < j
            return x
        return (0, min(x[1], y[1] - 1))

    # unary operators
    # ===============

    def _visit_invert(self, node, x):
        if x[0] > 0:
            return (0, 0)
        elif x == (0, 0):
            return (1, 1)
        else:
            return (0, 1)

    # comparison operators
    # ====================

    def _visit_gte(self, node, x, y):
        assert (x is not None) and (y is not None)
        return (
            x[0] >= y[1],
            x[1] >= y[0],
        )

    def _visit_gt(self, node, x, y):
        assert (x is not None) and (y is not None)
        return (
            x[0] > y[1],
            x[1] > y[0],
        )

    def _visit_lte(self, node, x, y):
        assert (x is not None) and (y is not None)
        return (
            x[1] <= y[0],
            x[0] <= y[1],
        )

    def _visit_lt(self, node, x, y):
        assert (x is not None) and (y is not None)
        return (
            x[1] < y[0],
            x[0] < y[1],
        )

    def _visit_eq(self, node, x, y):
        assert (x is not None) and (y is not None)
        if x[0] == x[1] == y[0] == y[1]:
            return (1, 1)
        if x[0] <= y[0] <= x[1]:
            return (0, 1)
        if y[0] <= x[0] <= y[1]:
            return (0, 1)
        return (0, 0)

    def _visit_noteq(self, node, x, y):
        assert (x is not None) and (y is not None)
        if x[0] == x[1] == y[0] == y[1]:
            return (0, 0)
        if x[0] <= y[0] <= x[1]:
            return (0, 1)
        if y[0] <= x[0] <= y[1]:
            return (0, 1)
        return (1, 1)

    # boolean operators
    # =================

    def _visit_and(self, node, *args):
        r = (1, 1)
        for arg in args:
            assert r != (0, 0)
            x = self._visit(arg)
            if x is None:
                if r == (0, 1):
                    return (0, 0)
                else:
                    return
            elif x == (0, 0):
                return x
            elif x[0] >= 1:
                pass
            else:
                assert (x[0] == 0) and (x[1] > 0)
                r = (0, 1)
        return r

    def _visit_or(self, node, *args):
        r = (0, 0)
        for arg in args:
            assert r != (1, 1)
            x = self._visit(arg)
            if x is None:
                if r == (0, 1):
                    return (1, 1)
                else:
                    return
            elif x[0] >= 1:
                return (1, 1)
            elif x == (0, 0):
                pass
            else:
                assert (x[0] == 0) and (x[1] > 0)
                r = (0, 1)
        return r

    # if-then-else expression
    # =======================

    def _visit_ifexp(self, node):
        test = self._visit(node.test)
        if test is None:
            return
        x = y = None
        if test[1] > 0:
            x = self._visit(node.body)
        if test[0] == 0:
            y = self._visit(node.orelse)
        if x is None:
            return y
        if y is None:
            return x
        return (
            min(x[0], y[0]),
            max(x[1], y[1]),
        )

    # contants, variables
    # ===================

    def _visit_num(self, node):
        n = node.n
        if (n < 0) or (n >= self._ctxt.max):
            return
        return (n, n)

    def _visit_name(self, node):
        return (0, self._ctxt.max - 1)

class Expression(object):

    def __init__(self, s):
        module = ast.parse('({})'.format(s), filename='<intexpr>')
        compile(module, '', 'exec')
        assert isinstance(module, ast.Module)
        [node] = ast.iter_child_nodes(module)
        assert isinstance(node, ast.Expr)
        self._node = node

    def __call__(self, n, *, bits=32):
        '''
        return f(n)
        '''
        e = Evaluator(self._node, n, bits=bits)
        return e()

    def codomain(self, *, bits=32):
        '''
        return
        * (i, j) such that for every n, f(n) ∈ {i, i+1, …, j}
        * or None
        '''
        e = CodomainEvaluator(self._node, bits=bits)
        return e()

# vim:ts=4 sts=4 sw=4 et
