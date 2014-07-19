'''
Sphinx configuration file for readthedocs.org
'''

import os
import re
import shutil

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
source_suffix = '.txt'
master_doc = 'index'
here = os.path.dirname(__file__)
path = os.path.join(here, os.pardir, project + source_suffix)
with open(path, 'rb') as file:
    content = file.read()
path = os.path.join(here, master_doc + source_suffix)
match =_header_re.search(content)
section = int(match.group('section'))
release = version = match.group('version')
description = match.group('description')
content = _header_re.sub('', content, count=1)
with open(path, 'wb') as file:
    file.write(content)
del content
shutil.copy(
    os.path.join(here, os.pardir, 'tags.txt'),
    os.path.join(here, 'tags.txt'),
)
exclude_patterns = ['tags.txt']

html_use_smartypants = False
html_theme_options = dict(nosidebar=True)
html_show_copyright = False
html_show_sphinx = False

# vim:ts=4 sw=4 et
