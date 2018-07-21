# encoding=UTF-8

# Copyright © 2014-2018 Jakub Wilk <jwilk@jwilk.net>
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
Sphinx configuration file for readthedocs.org
'''

import io
import os
import re
import subprocess as ipc

_header_re = re.compile(r'''
-+\n
(?P<description>[\w, ]+)\n
-+\n
\n
:manual[ ]section:[ ](?P<section>[0-9]+)\n
:version:[ ](i18nspector)[ ](?P<version>[0-9.]+)\n
:date:[ ][|]date[|]\n
''', re.VERBOSE
)

needs_sphinx = '1.0'
project = 'i18nspector'
source_suffix = '.rst'
master_doc = 'index'
here = os.path.dirname(__file__)
path = os.path.join(here, os.pardir, 'manpage.rst')
with io.open(path, 'rt', encoding='UTF-8') as file:
    content = file.read()
path = os.path.join(here, master_doc + source_suffix)
match = _header_re.search(content)
section = int(match.group('section'))
release = version = match.group('version')
description = match.group('description')
content = _header_re.sub('', content, count=1)
with io.open(path, 'wt', encoding='UTF-8') as file:
    file.write(content)
del content

tags_rst = os.path.join(here, 'tags' + source_suffix)
with open(tags_rst, 'wb') as file:
    generator_path = os.path.join(
        os.pardir, os.pardir,
        'private', 'tags-as-rst',
    )
    ipc.check_call([generator_path], stdout=file)
exclude_patterns = [os.path.basename(tags_rst)]

html_use_smartypants = False
html_theme = 'sphinxdoc'
html_theme_options = dict(nosidebar=True)
html_show_copyright = False
html_show_sphinx = False

# vim:ts=4 sts=4 sw=4 et
