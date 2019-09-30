# Copyright © 2012-2018 Jakub Wilk <jwilk@jwilk.net>
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
color terminal support
'''

import functools
import re

class _dummy_curses:

    @staticmethod
    def tigetstr(*args, **kwargs):
        del args, kwargs
        return b''

    @staticmethod
    def tparm(*args, **kwargs):
        del args, kwargs
        return b''

_curses = _dummy_curses

class colors:
    black = NotImplemented
    red = NotImplemented
    green = NotImplemented
    yellow = NotImplemented
    blue = NotImplemented
    magenta = NotImplemented
    cyan = NotImplemented
    white = NotImplemented

_strip_delay = functools.partial(
    re.compile(b'[$]<([0-9]*[.])?[0-9]+([/*]|[*][/])?>').sub,
    b''
)

def attr_fg(i):
    '''
    returns a string that changes the foreground color
    '''
    s = _curses.tigetstr('setaf') or b''
    s = _strip_delay(s)
    if s:  # work-around for https://bugs.debian.org/902630
        s = _curses.tparm(s, i)
    return s.decode()

def attr_reset():
    '''
    returns a string that resets all attributes
    '''
    s = _curses.tigetstr('sgr0') or b''
    s = _strip_delay(s)
    return s.decode()

def initialize():
    '''
    initialize the terminal
    '''
    global _curses  # pylint: disable=global-statement
    try:
        import curses as _curses  # pylint: disable=redefined-outer-name,import-outside-toplevel
    except ImportError:
        return
    try:
        _curses.setupterm()
    except _curses.error:
        _curses = _dummy_curses
        return
    for key, value in vars(_curses).items():
        if key.startswith('COLOR_'):
            key = key[6:].lower()
            getattr(colors, key)
            setattr(colors, key, value)

# vim:ts=4 sts=4 sw=4 et
