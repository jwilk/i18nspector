# Copyright © 2012-2016 Jakub Wilk <jwilk@jwilk.net>
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
C integer expressions
'''

import ast
import functools
import types

import rply
import rply.errors

LexingError = rply.errors.LexingError
ParsingError = rply.errors.ParsingError

# https://git.savannah.gnu.org/cgit/gettext.git/tree/gettext-runtime/intl/plural.y?id=v0.18.3#n132

@functools.lru_cache(maxsize=None)
def create_lexer():
    lg = rply.LexerGenerator()
    lg.add('IF', r'[?]')
    lg.add('ELSE', r':')
    lg.add('OR', r'[|][|]')
    lg.add('AND', r'[&][&]')
    lg.add('EQ', r'[!=]=')
    lg.add('CMP', r'[<>]=?')
    lg.add('ADDSUB', r'[+-]')
    lg.add('MULDIV', r'[*/%]')
    lg.add('NOT', r'!')
    lg.add('LPAR', r'[(]')
    lg.add('RPAR', r'[)]')
    lg.add('VAR', r'n')
    lg.add('INT', r'[0-9]+')
    lg.ignore(r'[ \t]+')
    return lg.build()

@functools.lru_cache(maxsize=None)
def create_parser(lexer):
    pg = rply.ParserGenerator(
        [rule.name for rule in lexer.rules],
        precedence=[
            ('right', ['IF', 'ELSE']),
            ('left', ['OR']),
            ('left', ['AND']),
            ('left', ['EQ']),
            ('left', ['CMP']),
            ('left', ['ADDSUB']),
            ('left', ['MULDIV']),
            ('right', ['NOT']),
        ],
        cache_id='i18nspector-intexpr',
    )
    ast_bool = {
        '&&': ast.And(),
        '||': ast.Or(),
    }
    ast_cmp = {
        '==': ast.Eq(),
        '!=': ast.NotEq(),
        '<': ast.Lt(),
        '<=': ast.LtE(),
        '>': ast.Gt(),
        '>=': ast.GtE(),
    }
    ast_arithmetic = {
        '+': ast.Add(),
        '-': ast.Sub(),
        '*': ast.Mult(),
        '/': ast.Div(),
        '%': ast.Mod(),
    }
    ast_not = ast.Not()
    # pylint: disable=unused-variable
    @pg.production('start : exp')
    def eval_start(p):
        [exp] = p
        return ast.Expr(exp)
    @pg.production('exp : exp IF exp ELSE exp')
    def expr_ifelse(p):
        [cond, _, body, _, orelse] = p
        return ast.IfExp(cond, body, orelse)
    @pg.production('exp : exp OR exp')
    @pg.production('exp : exp AND exp')
    def expr_bool(p):
        [left, tok, right] = p
        op = ast_bool[tok.getstr()]
        return ast.BoolOp(op, [left, right])
    @pg.production('exp : exp EQ exp')
    @pg.production('exp : exp CMP exp')
    def expr_cmp(p):
        [left, tok, right] = p
        op = ast_cmp[tok.getstr()]
        return ast.Compare(left, [op], [right])
    @pg.production('exp : exp ADDSUB exp')
    @pg.production('exp : exp MULDIV exp')
    def expr_arithmetic(p):
        [left, tok, right] = p
        op = ast_arithmetic[tok.getstr()]
        return ast.BinOp(left, op, right)
    @pg.production('exp : NOT exp')
    def expr_not(p):
        [_, value] = p
        return ast.UnaryOp(ast_not, value)
    @pg.production('exp : LPAR exp RPAR')
    def expr_par(p):
        [_, exp, _] = p
        return exp
    @pg.production('exp : VAR')
    def expr_var(p):
        [tok] = p
        ident = tok.getstr()
        assert ident == 'n'
        return ast.Name(ident, ast.Load())
    @pg.production('exp : INT')
    def expr_int(p):
        [tok] = p
        n = int(tok.getstr())
        return ast.Num(n)
    # pylint: enable=unused-variable
    with misc.throwaway_tempdir('rply'):
        # Use private temporary directory
        # to mitigate RPLY's insecure use of /tmp:
        # CVE-2014-1604, CVE-2014-1938
        return pg.build()

class Parser(object):

    def __init__(self):
        self._lexer = create_lexer()
        self._parser = create_parser(self._lexer)

    def parse(self, s):
        tokens = self._lexer.lex(s)
        node = self._parser.parse(tokens)
        return Expression(node)

from lib import misc  # pylint: disable=wrong-import-position

class BaseEvaluator(object):

    def __init__(self, node):
        self._ctxt = types.SimpleNamespace()
        self._node = node

    def __call__(self):
        node = self._node
        assert isinstance(node, ast.Expr)
        return self._visit_expr(node)

    def _visit(self, node, *args):
        try:
            fn = getattr(self, '_visit_' + type(node).__name__.lower())
        except KeyError:  # no coverage
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
        assert len(node.comparators) == len(node.ops)
        if len(node.ops) != 1:
            raise NotImplementedError
        left = node.left
        [op] = node.ops
        [right] = node.comparators
        left = self._visit(left)
        if left is None:
            return
        right = self._visit(right)
        if right is None:
            return
        return self._visit(op, left, right)

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

    # pylint: disable=unused-argument

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

    def _visit_not(self, node, x):
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

    # constants, variables
    # ====================

    def _visit_num(self, node):
        return self._check_overflow(node.n)

    def _visit_name(self, node):
        return self._check_overflow(self._ctxt.n)

    # pylint: enable=unused-argument

class CodomainEvaluator(BaseEvaluator):

    def __init__(self, node, *, bits):
        super().__init__(node)
        self._ctxt.max = 1 << bits

    # pylint: disable=unused-argument

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

    def _visit_not(self, node, x):
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

    # constants, variables
    # ====================

    def _visit_num(self, node):
        n = node.n
        if (n < 0) or (n >= self._ctxt.max):
            return
        return (n, n)

    def _visit_name(self, node):
        return (0, self._ctxt.max - 1)

    # pylint: enable=unused-argument

def gcd(x, y):
    while y:
        (x, y) = (y, x % y)
    return x

def lcm(x, *ys):
    r = x
    for y in ys:
        r //= gcd(r, y)
        r *= y
    return r

class PeriodEvaluator(BaseEvaluator):

    def __init__(self, node, *, bits):
        super().__init__(node)
        self._ctxt.max = 1 << bits

    # binary operators
    # ================

    def _visit_binop(self, node):
        const_mod = (
            isinstance(node.op, ast.Mod) and
            isinstance(node.left, ast.Name) and
            isinstance(node.right, ast.Num)
        )
        if const_mod:
            n = node.right.n
            if (n <= 0) or (n >= self._ctxt.max):
                return
            return (0, n)
        x = self._visit(node.left)
        if x is None:
            return
        y = self._visit(node.right)
        if y is None:
            return
        (xo, xp) = x
        (yo, yp) = y
        ro = max(xo, yo)
        rp = lcm(xp, yp)
        if rp >= self._ctxt.max:
            return
        else:
            return (ro, rp)

    # unary operators
    # ===============

    def _visit_unaryop(self, node):
        return self._visit(node.operand)

    # comparison operators
    # ====================

    def _visit_compare(self, node):
        assert len(node.comparators) == len(node.ops)
        if len(node.ops) != 1:
            raise NotImplementedError
        [op] = node.ops
        [right] = node.comparators
        const_cmp = (
            isinstance(node.left, ast.Name) and
            isinstance(right, ast.Num)
        )
        if const_cmp:
            n = right.n
            if (n < 0) or (n >= self._ctxt.max):
                return
            # (n <cmp> N) is constant starting with either N or N+1,
            # depending on <cmp>:
            #
            #        …N-1  N  N+1 N+2…
            # -------+---+---+---+----
            # n != N | 1 . 0 . 1 . 1
            # n == N | 0 . 1 . 0 . 0
            # n <= N | 1 . 1 . 0 . 0
            # n >  N | 0 . 0 . 1 . 1
            # -------+---+---+---+----
            # n <  N | 1 . 0 . 0 . 0
            # n >= N | 0 . 1 . 1 . 1
            # -------+---+---+---+----
            if isinstance(op, (ast.Lt, ast.GtE)):
                return (n, 1)
            else:
                if n + 1 == self._ctxt.max:
                    return
                return (n + 1, 1)
        x = self._visit(node.left)
        if x is None:
            return
        y = self._visit(right)
        if y is None:
            return
        (xo, xp) = x
        (yo, yp) = y
        ro = max(xo, yo)
        rp = lcm(xp, yp)
        if rp >= self._ctxt.max:
            return
        else:
            return (ro, rp)

    # boolean operators
    # =================

    def _visit_boolop(self, node):
        (xo, xp) = (0, 1)
        for arg in node.values:
            y = self._visit(arg)
            if y is None:
                return
            (yo, yp) = y
            xo = max(xo, yo)
            xp = lcm(xp, yp)
            if xp >= self._ctxt.max:
                return
        return (xo, xp)

    # if-then-else expression
    # =======================

    def _visit_ifexp(self, node):
        test = self._visit(node.test)
        if test is None:
            return
        (to, tp) = test
        x = self._visit(node.body)
        if x is None:
            return
        (xo, xp) = x
        y = self._visit(node.orelse)
        if y is None:
            return
        (yo, yp) = y
        ro = max(to, xo, yo)
        rp = lcm(tp, xp, yp)
        if rp >= self._ctxt.max:
            return
        else:
            return (ro, rp)

    # constants, variables
    # ====================

    def _visit_num(self, node):
        n = node.n
        if n < 0 or n >= self._ctxt.max:
            return
        return (0, 1)

    def _visit_name(self, node):  # pylint: disable=unused-argument
        return

class Expression(object):

    def __init__(self, node):
        if not isinstance(node, ast.Expr):
            raise TypeError  # no coverage
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
        * (L, R) such that for every n: L ≤ f(n) ≤ R
        * or None
        '''
        e = CodomainEvaluator(self._node, bits=bits)
        return e()

    def period(self, *, bits=32):
        '''
        return
        * (O, P) such that for every n ≥ O: f(n + P) = f(n)
        * or None
        '''
        e = PeriodEvaluator(self._node, bits=bits)
        return e()

# vim:ts=4 sts=4 sw=4 et
