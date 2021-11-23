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

import os

import tests.tools

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

# vim:ts=4 sts=4 sw=4 et
