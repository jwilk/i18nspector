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
miscellanea
'''

import contextlib
import datetime
import sys
import tempfile
import types

def unsorted(iterable):
    '''
    if the iterable is sorted, return None;
    otherwise return first (x, y) such that x > y
    '''
    iterable = iter(iterable)
    for x in iterable:
        break
    for y in iterable:
        if x > y:
            return (x, y)
        x = y

class DataIntegrityError(Exception):
    pass

def check_sorted(iterable, exception=DataIntegrityError):
    '''
    raise exception if the iterable is not sorted
    '''
    cx = unsorted(iterable)
    if cx is not None:
        raise exception('{0!r} > {1!r}'.format(*cx))

def sorted_vk(d):
    '''
    iterate over d.values() in the key order
    '''
    for k, v in sorted(d.items()):
        del k
        yield v

def utc_now():
    '''
    timezone-aware variant of datetime.now()
    '''
    return datetime.datetime.now(
        datetime.timezone.utc
    )

def format_range(rng, *, max):
    last = rng[-1]
    result = []
    if max < 4:
        raise ValueError('max must be >= 4')
    for i in rng:
        if len(result) < max:
            result += [i]
        else:
            result[-2:] = ['...', str(last)]
            break
    return ', '.join(map(str, result))

class Namespace(object):
    '''
    simple attribute-based namespace
    '''
    def __init__(self, **kwargs):
        super().__init__()
        self.__dict__.update(kwargs)

Namespace()  # make pyflakes and coverage.py happy

if sys.version_info >= (3, 3):  # <no-coverage>
    Namespace = types.SimpleNamespace

@contextlib.contextmanager
def throwaway_tempdir(context):
    with tempfile.TemporaryDirectory(prefix='i18nspector.{}.'.format(context)) as new_tempdir:
        original_tempdir = tempfile.tempdir
        try:
            tempfile.tempdir = new_tempdir
            yield
        finally:
            tempfile.tempdir = original_tempdir

# vim:ts=4 sts=4 sw=4 et
