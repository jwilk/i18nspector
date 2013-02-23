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

import argparse
import io
import os
import shutil
import subprocess as ipc
import sys
import tempfile

from . import checker
from . import encodings
from . import gettext
from . import ling
from . import misc
from . import tags
from . import terminal

__version__ = '0.8.1'

def initialize_terminal():
    if sys.stdout.isatty():
        terminal.initialize()
    if sys.stdout.errors != 'strict':
        return
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
        encoding=sys.stdout.encoding,
        errors='backslashreplace',
    )

class Checker(checker.Checker):

    def tag(self, tagname, *extra):
        if tagname in self.options.ignore_tags:
            return
        tag = self.options.taginfo[tagname]
        s = tag.format(self.fake_path, *extra, color=True)
        print(s)

def check_file(filename, *, options):
    checker_instance = Checker(filename, options=options)
    checker_instance.check()

def copy_options(options, **update):
    kwargs = vars(options)
    kwargs.update(update)
    return argparse.Namespace(**kwargs)

class UnsupportedFileType(ValueError):
    pass

def check_deb(filename, *, options):
    if filename.endswith('.deb'):
        binary = True
    elif filename.endswith('.dsc'):
        binary = False
    else:
        raise UnsupportedFileType
    tmpdir = tempfile.mkdtemp(prefix='i18nspector.deb.')
    ignore_tags = set(options.ignore_tags)
    ignore_tags.add('unknown-file-type')
    try:
        if binary:
            ipc.check_call(['dpkg-deb', '-x', filename, tmpdir])
            real_root = os.path.join(tmpdir, '')
        else:
            real_root = os.path.join(tmpdir, 's', '')
            with open(os.devnull) as bitbucket:
                ipc.check_call(
                    ['dpkg-source', '--no-copy', '--no-check', '-x', filename, real_root],
                    stdout=bitbucket # dpkg-source would be noisy without this...
                )
        options = copy_options(options,
            ignore_tags=ignore_tags,
            fake_root=(real_root, os.path.join(filename, ''))
        )
        for root, dirs, files in os.walk(tmpdir):
            for path in files:
                path = os.path.join(root, path)
                if os.path.islink(path):
                    continue
                if os.path.isfile(path):
                    check_file(path, options=options)
    finally:
        shutil.rmtree(tmpdir)

def main(basedir):
    initialize_terminal()
    is_like_debian = misc.OSRelease().is_like('debian')
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__))
    ap.add_argument('-l', '--language', metavar='<lang>', help='assume this langauge')
    debian_help = 'allow checking Debian packages' + (' (enabled on this system)' if is_like_debian else '')
    ap.add_argument('--debian', action='store_true', default=is_like_debian, help=debian_help)
    ap.add_argument('--traceback', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('files', metavar='<file>', nargs='+')
    options = ap.parse_args()
    files = options.files
    del options.files
    datadir = os.path.join(
        basedir,
        'data', ''
    )
    os.stat(datadir)
    options.encinfo = encinfo = encodings.EncodingInfo(datadir)
    options.gettextinfo = gettext.GettextInfo(datadir)
    options.linginfo = linginfo = ling.LingInfo(datadir)
    options.taginfo = tags.TagInfo(datadir)
    if options.language is not None:
        try:
            language = linginfo.parse_language(options.language)
            language.fix_codes()
        except ling.LanguageError:
            if options.traceback:
                raise
            ap.error('invalid language')
        language.remove_encoding()
        language.remove_nonlinguistic_modifier()
        options.language = language
    options.ignore_tags = set()
    options.fake_root = None
    with Checker.patched_environment(encinfo):
        check_all(files, options=options)

def check_all(files, *, options):
    for filename in files:
        if options.debian:
            try:
                check_deb(filename, options=options)
            except UnsupportedFileType:
                pass
            else:
                continue
        check_file(filename, options=options)

# vim:ts=4 sw=4 et
