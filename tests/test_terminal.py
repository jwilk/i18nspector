# Copyright © 2012-2024 Jakub Wilk <jwilk@jwilk.net>
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
import pty
import sys

import lib.terminal as T

from .tools import (
    assert_equal,
)

from . import tools

def test_strip_delay():
    def t(s, r=b''):
        assert_equal(T._strip_delay(s), r)  # pylint: disable=protected-access
    t(b'$<1>')
    t(b'$<2/>')
    t(b'$<3*>')
    t(b'$<4*/>')
    t(b'$<.5*/>')
    t(b'$<0.6*>')
    s = b'$<\x9B20>'
    t(s, s)

def _get_colors():
    return (
        value
        for name, value in sorted(vars(T.colors).items())
        if name.isalpha()
    )

def assert_tseq_equal(s, expected):
    class S(str):
        # assert_equal() does detailed comparison for instances of str,
        # but not their subclasses. We don't want detailed comparisons,
        # because diff could contain control characters.
        pass
    assert_equal(S(expected), S(s))

def test_dummy():
    t = assert_tseq_equal
    for i in _get_colors():
        t(T.attr_fg(i), '')
    t(T.attr_reset(), '')

def pty_fork_isolation(term):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            (master_fd, slave_fd) = pty.openpty()
            os.dup2(slave_fd, pty.STDOUT_FILENO)
            os.close(slave_fd)
            sys.stdout = sys.__stdout__
            os.environ['TERM'] = term
            T.initialize()
            try:
                return func(*args, **kwargs)
            finally:
                os.close(master_fd)
        return tools.fork_isolation(wrapper)
    return decorator

@pty_fork_isolation('vt100')
def test_vt100():
    t = assert_tseq_equal
    for i in _get_colors():
        t(T.attr_fg(i), '')
    t(T.attr_reset(), '\33[m\17')

@pty_fork_isolation('ansi')
def test_ansi():
    t = assert_tseq_equal
    t(T.attr_fg(T.colors.black), '\33[30m')
    t(T.attr_fg(T.colors.red), '\33[31m')
    t(T.attr_fg(T.colors.green), '\33[32m')
    t(T.attr_fg(T.colors.yellow), '\33[33m')
    t(T.attr_fg(T.colors.blue), '\33[34m')
    t(T.attr_fg(T.colors.magenta), '\33[35m')
    t(T.attr_fg(T.colors.cyan), '\33[36m')
    t(T.attr_fg(T.colors.white), '\33[37m')
    t(T.attr_reset(), '\33[0;10m')

# vim:ts=4 sts=4 sw=4 et
