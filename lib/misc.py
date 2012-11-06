# Copyright © 2012 Jakub Wilk <jwilk@jwilk.net>
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
import warnings

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

class NotOverriddenWarning(UserWarning):
    pass

def not_overridden(f):
    '''
    Issue NotOverriddenWarning if the decorated method was not overridden in a
    subclass, or called directly.
    '''
    @functools.wraps(f)
    def new_f(self, *args, **kwargs):
        cls = type(self)
        warnings.warn(
            '%s.%s.%s() is not overridden' % (cls.__module__, cls.__name__, f.__name__),
            category=NotOverriddenWarning,
            stacklevel=2
        )
        return f(self, *args, **kwargs)
    return new_f

# vim:ts=4 sw=4 et
