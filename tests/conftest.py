# encoding=UTF-8

# Copyright © 2021 Stuart Prescott <stuart@debian.org>
# Copyright © 2021 Jakub Wilk <jwilk@jwilk.net>
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

import inspect
import os
import sys
import unittest

import pytest

import tests.tools

if sys.version_info < (3, 6):
    raise RuntimeError('Python >= 3.6 is required for pytest support')

def _make_method(fn, args):
    def _test_item(self):
        del self
        return fn(*args)
    return _test_item

def _make_skip_func(exc):
    def test(self=None):
        raise exc
    return test

if int(pytest.__version__.split('.', 1)[0]) < 6:
    # pytest before 6.0 doesn't like "[" in the test name
    # https://github.com/pytest-dev/pytest/commit/8b9b81c3c04399d0
    def _mangle_test_name(s):
        return s.replace('[', '(').replace(']', ')')
else:
    _mangle_test_name = str

def _collect_yielded(generator):
    genargs = list(inspect.signature(generator).parameters.keys())
    if genargs == ['self']:
        class YieldTestDescriptor():
            def __set_name__(self, owner, name):
                try:
                    args_lst = list(generator(owner()))
                except unittest.SkipTest as exc:
                    skip_method = _make_skip_func(exc)
                    setattr(owner, name, skip_method)
                    return
                for args in args_lst:
                    fn, *args = args
                    aname = name + repr(args)
                    aname = _mangle_test_name(aname)
                    assert getattr(owner, aname, None) is None
                    setattr(owner, aname, _make_method(fn, args))
        return YieldTestDescriptor()
    elif genargs == []:  # pylint: disable=use-implicit-booleaness-not-comparison
        class Test():
            pass
        try:
            args_lst = list(generator())
        except unittest.SkipTest as exc:
            return _make_skip_func(exc)
        for args in args_lst:
            fn, *args = args
            aname = 'test' + repr(args)
            aname = _mangle_test_name(aname)
            assert getattr(Test, aname , None) is None
            setattr(Test, aname, _make_method(fn, args))
        Test.__module__ = generator.__module__
        Test.__name__ = generator.__name__
        Test.__qualname__ = generator.__qualname__
        return Test
    else:
        raise RuntimeError

def pytest_sessionstart(session):
    envvar = 'XDG_CACHE_HOME'
    old_xdg_cache_home = os.environ.get(envvar, None)
    xdg_temp_dir = tests.tools.temporary_directory()  # pylint: disable=consider-using-with
    os.environ[envvar] = xdg_temp_dir.name
    def cleanup():
        xdg_temp_dir.cleanup()
        if old_xdg_cache_home is None:
            del os.environ[envvar]
        else:
            os.environ[envvar] = old_xdg_cache_home
    session.config.add_cleanup(cleanup)
    tests.tools.collect_yielded = _collect_yielded

# vim:ts=4 sts=4 sw=4 et
