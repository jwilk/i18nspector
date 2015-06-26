# Copyright © 2012-2013 Jakub Wilk <jwilk@jwilk.net>
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

import pty
import os
import sys

from nose.tools import (
    assert_equal,
)

from . import aux

import lib.terminal as T

def test_strip_delay():
    def t(s, r=b''):
        assert_equal(T._strip_delay(s), r)
    t(b'$<1>')
    t(b'$<2/>')
    t(b'$<3*>')
    t(b'$<4*/>')
    t(b'$<.5*/>')
    t(b'$<0.6*>')
    s = b'$<\x9b20>'
    t(s, s)

def _get_colors():
    return (
        value
        for name, value in sorted(vars(T.colors).items())
        if name.isalpha()
    )

def test_dummy():
    for i in _get_colors():
        assert_equal(T.attr_fg(i), '')
    assert_equal(T.attr_reset(), '')

def _setup_tty(term):
    master_fd, slave_fd = pty.openpty()
    os.dup2(slave_fd, pty.STDOUT_FILENO)
    sys.stdout = sys.__stdout__
    os.environ['TERM'] = term
    T.initialize()

@aux.fork_isolation
def test_vt100():
    _setup_tty('vt100')
    for i in _get_colors():
        assert_equal(T.attr_fg(i), '')
    assert_equal(T.attr_reset(), '\x1b[m\x0f')

@aux.fork_isolation
def test_ansi():
    _setup_tty('ansi')
    assert_equal(T.attr_fg(T.colors.black), '\x1b[30m')
    assert_equal(T.attr_fg(T.colors.red), '\x1b[31m')
    assert_equal(T.attr_fg(T.colors.green), '\x1b[32m')
    assert_equal(T.attr_fg(T.colors.yellow), '\x1b[33m')
    assert_equal(T.attr_fg(T.colors.blue), '\x1b[34m')
    assert_equal(T.attr_fg(T.colors.magenta), '\x1b[35m')
    assert_equal(T.attr_fg(T.colors.cyan), '\x1b[36m')
    assert_equal(T.attr_fg(T.colors.white), '\x1b[37m')
    assert_equal(T.attr_reset(), '\x1b[0;10m')

# vim:ts=4 sts=4 sw=4 et
