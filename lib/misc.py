# Copyright © 2012, 2013 Jakub Wilk <jwilk@jwilk.net>
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

import datetime
import errno
import shlex

def is_sorted(iterable):
    # It's not very efficient, but should be enough for our purposes.
    lst1 = list(iterable)
    lst2 = sorted(lst1)
    return lst1 == lst2

class DataIntegrityError(Exception):
    pass

def check_sorted(iterable, exception=DataIntegrityError):
    if not is_sorted(iterable):
        raise exception()

def utc_now():
    now = datetime.datetime.now()
    now = now.replace(tzinfo=datetime.timezone.utc)
    return now

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

# vim:ts=4 sw=4 et
