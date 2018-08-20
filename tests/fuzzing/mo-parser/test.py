# Copyright © 2015-2018 Jakub Wilk <jwilk@jwilk.net>
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

import encodings
import importlib
import os
import pkgutil
import sys

import afl

sys.path[0] += '/../../..'

import tests.tools
import lib.moparser as M

temporary_file = tests.tools.temporary_file

def parser_for_bytes(data):
    with temporary_file(suffix='.mo') as file:
        file.write(data)
        file.flush()
        return M.Parser(file.name)

def test(data):
    try:
        parser_for_bytes(data)
    except M.SyntaxError:
        return
    except UnicodeDecodeError:
        pass

def main():
    for _, modname, _ in pkgutil.iter_modules(encodings.__path__, prefix='encodings.'):
        try:
            importlib.import_module(modname)
        except (LookupError, ImportError):
            pass
    while afl.loop(max=1000):
        data = sys.stdin.buffer.read()  # pylint: disable=no-member
        test(data)
    os._exit(0)  # pylint: disable=protected-access

if __name__ == '__main__':
    main()

# vim:ts=4 sts=4 sw=4 et
