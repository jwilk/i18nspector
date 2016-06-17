# Copyright © 2013 Jakub Wilk <jwilk@jwilk.net>
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
desktop entry parser
'''

# http://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-1.0.html

import collections
import re

class SyntaxError(Exception):

    def __init__(self):
        raise NotImplementedError

class InvalidGroupName(SyntaxError):
    def __init__(self, lineno, group_name):
        self.lineno = lineno
        self.group_name = group_name

class DuplicateGroup(SyntaxError):
    def __init__(self, lineno, group_name):
        self.lineno = lineno
        self.group_name = group_name

class InvalidKeyName(SyntaxError):

    def __init__(self, lineno, group_name, key):
        self.lineno = lineno
        self.group_name = group_name
        self.key = key

class DuplicateKey(SyntaxError):
    def __init__(self, lineno, group_name, key):
        self.lineno = lineno
        self.group_name = group_name
        self.key = key

class StrayLine(SyntaxError):
    def __init__(self, lineno, line):
        self.lineno = lineno
        self.line = line

class Entry(object):

    def __init__(self, lineno, key, raw_value, encoding='UTF-8'):
        self.lineno = lineno
        self.key = key
        self.raw_value = raw_value
        self.encoding = encoding

    @property
    def value(self):
        return self.raw_value.decode(self.encoding)

    def __str__(self):
        return '{} = {}'.format(self.key, self.value)

_is_valid_group_name = re.compile(
    br'\A [\x20-\x5A\x5C\x5E-\x7E]+ \Z',
    re.VERBOSE
).match

_is_valid_entry_name = re.compile(
    br'\A [A-Za-z0-9-]+ ( \[ [A-Za-z0-9@_-]+ \] )? \Z',
    re.VERBOSE
).match

def parse_desktop_entry(file):
    # This parser is not as strict as it could be. This is by design: it's not
    # our job to report general syntax errors.
    if not isinstance(file.read(0), bytes):
        raise TypeError
    result = collections.OrderedDict()
    group = group_name = None
    for lineno, line in enumerate(file):
        line = line.rstrip(b'\n')
        if line[:1] in {b'', b'#'}:
            # TODO: "using UTF-8 for comment lines that contain characters not
            # in ASCII is encouraged"
            continue
        elif line[:1] == b'[' and line[-1:] == b']':
            group_name = line[1:-1]
            if not _is_valid_group_name(group_name):
                raise InvalidGroupName(lineno, group_name)
            group_name = group_name.decode('ASCII')
            if group_name in result:
                raise DuplicateGroup(lineno, group_name)
            result[group_name] = group = collections.OrderedDict()
        else:
            if group is None:
                raise StrayLine(lineno, line)
            assert isinstance(group, dict)
            assert isinstance(group_name, str)
            try:
                key, value = line.split(b'=', 1)
            except ValueError:
                raise StrayLine(lineno, line)
            key = key.rstrip()
            if not _is_valid_entry_name(key):
                raise InvalidKeyName(lineno, group_name, key)
            key = key.decode('ASCII')
            value = value.lstrip()
            entry = Entry(lineno, key, value)
            if key in group:
                raise DuplicateKey(lineno, group_name, key)
            group[key] = entry
    return result

def main():
    import argparse
    ap = argparse.ArgumentParser('desktop entry parser')
    ap.add_argument('file', metavar='<file>')
    options = ap.parse_args()
    path = options.file
    with open(path, 'rb') as file:
        print('# {}'.format(path))
        result = parse_desktop_entry(file)
        for group_name, group in result.items():
            print('[{}]'.format(group_name))
            for entry in group.values():
                print(entry)

if __name__ == '__main__':
    main()
else:
    del main

# vim:ts=4 sw=4 et
