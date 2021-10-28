# Copyright © 2014-2017 Jakub Wilk <jwilk@jwilk.net>
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

import random

import pytest

import lib.moparser as M

from . import tools

def parser_for_bytes(data):
    with tools.temporary_file(suffix='.mo') as file:
        file.write(data)
        file.flush()
        return M.Parser(file.name)

class test_magic:

    def test_value(self):
        assert M.little_endian_magic == b'\xDE\x12\x04\x95'
        assert M.big_endian_magic == b'\x95\x04\x12\xDE'

    def test_short(self):
        for j in range(0, 3):
            data = M.little_endian_magic[:j]
            with pytest.raises(M.SyntaxError) as cm:
                parser_for_bytes(data)
            assert str(cm.value) == 'unexpected magic'

    def test_full(self):
        for magic in {M.little_endian_magic, M.big_endian_magic}:
            with pytest.raises(M.SyntaxError) as cm:
                parser_for_bytes(magic)
            assert str(cm.value) == 'truncated file'

    def test_random(self):
        while True:
            random_magic = bytes(
                random.randrange(0, 0x100) for i in range(0, 4)
            )
            if random_magic in {M.little_endian_magic, M.big_endian_magic}:
                continue
            break
        with pytest.raises(M.SyntaxError) as cm:
            parser_for_bytes(random_magic)
        assert str(cm.value) == 'unexpected magic'

# vim:ts=4 sts=4 sw=4 et
