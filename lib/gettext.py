# Copyright © 2012-2018 Jakub Wilk <jwilk@jwilk.net>
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
gettext header support:
- header field names registry
- date parser
- plural expressions parser
- string formats registry
'''

import configparser
import datetime
import os
import re

from lib import intexpr
from lib import misc
from lib import paths

# =============
# header fields
# =============

def _read_header_fields():
    path = os.path.join(paths.datadir, 'header-fields')
    with open(path, 'rt', encoding='ASCII') as file:
        fields = [
            s.rstrip() for s in file
            if s.rstrip() and not s.startswith('#')
        ]
    misc.check_sorted(fields)
    return frozenset(fields)

header_fields = _read_header_fields()

# ==========================
# header and message parsing
# ==========================

is_valid_field_name = re.compile(r'^[\x21-\x39\x3B-\x7E]+$').match
# https://tools.ietf.org/html/rfc5322#section-3.6.8

def parse_header(s):
    lines = s.split('\n')
    if lines[-1] == '':
        lines.pop()
    for line in lines:
        key, *values = line.split(':', 1)
        if values and is_valid_field_name(key):
            assert len(values) == 1
            value = values[0].strip(' \t')
            yield {key: value}
        else:
            yield line

search_for_conflict_marker = re.compile(r'^#-#-#-#-#  .+  #-#-#-#-#$', re.MULTILINE).search
# https://git.savannah.gnu.org/cgit/gettext.git/tree/gettext-tools/src/msgl-cat.c?id=v0.18.3#n590
# https://www.gnu.org/software/gettext/manual/html_node/Creating-Compendia.html#Creating-Compendia

# ============
# plural forms
# ============

class PluralFormsSyntaxError(Exception):
    pass

class PluralExpressionSyntaxError(PluralFormsSyntaxError):
    pass

def parse_plural_expression(s):
    parser = intexpr.Parser()
    try:
        return parser.parse(s)
    except intexpr.LexingError:
        raise PluralExpressionSyntaxError
    except intexpr.ParsingError:
        raise PluralExpressionSyntaxError

_parse_plural_forms = re.compile(r'nplurals=([1-9][0-9]*);[ \t]*plural=([^;]+);?').search

def parse_plural_forms(s, strict=True):
    match = _parse_plural_forms(s)
    if match is None:
        raise PluralFormsSyntaxError
    n = int(match.group(1), 10)
    expr = parse_plural_expression(match.group(2))
    if strict:
        if match.start() != 0:
            raise PluralFormsSyntaxError
        if match.end() != len(s):
            raise PluralFormsSyntaxError
        return (n, expr)
    else:
        ljunk = s[:match.start()]
        rjunk = s[match.end():]
        return (n, expr, ljunk, rjunk)

# =====
# Dates
# =====

class DateSyntaxError(Exception):
    pass

class BoilerplateDate(DateSyntaxError):
    pass

def _read_timezones():
    path = os.path.join(paths.datadir, 'timezones')
    cp = configparser.ConfigParser(interpolation=None, default_section='')
    cp.optionxform = str
    cp.read(path, encoding='ASCII')
    return {
        abbrev: offsets.split()
        for abbrev, offsets in cp['timezones'].items()
    }

_timezones = _read_timezones()

_tz_re = '|'.join(re.escape(tz) for tz in _timezones)
_parse_date = re.compile(r'''
    ^
    ( [0-9]{4}-[0-9]{2}-[0-9]{2} )  # YYYY-MM-DD
    (?: \s+ | T )
    ( [0-9]{2}:[0-9]{2} )  # hh:mm
    (?: : [0-9]{2} )?  # ss
    \s*
    (?:
      (?: GMT | UTC )? ( [+-] [0-9]{2} ) :? ( [0-9]{2} )  # ZZzz
    | [+]? (''' + _tz_re + ''')
    ) ?
    $
''', re.VERBOSE).match

boilerplate_date = 'YEAR-MO-DA HO:MI+ZONE'

_search_for_date_boilerplate = re.compile(r'''
  ^ YEAR -
| - MO -
| - DA \s
| \s HO :
| : MI (?:[+]|$)
| [+] ZONE $
''', re.VERBOSE).search

def fix_date_format(s, *, tz_hint=None):
    s = s.strip()
    if _search_for_date_boilerplate(s):
        raise BoilerplateDate
    if tz_hint is not None:
        datetime.datetime.strptime(tz_hint, '%z')  # just check syntax
    match = _parse_date(s)
    if match is None:
        raise DateSyntaxError
    (date, time, zhour, zminute, zabbr) = match.groups()
    if (zhour is not None) and (zminute is not None):
        zone = zhour + zminute
    elif zabbr is not None:
        try:
            [zone] = _timezones[zabbr]
        except ValueError:
            raise DateSyntaxError('ambiguous timezone abbreviation: ' + zabbr)
    elif tz_hint is not None:
        zone = tz_hint
    else:
        raise DateSyntaxError
    s = '{} {}{}'.format(date, time, zone)
    assert len(s) == 21, 'len({!r}) != 21'.format(s)
    parse_date(s)  # just check syntax
    return s

def parse_date(s):
    try:
        return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M%z')
    except ValueError as exc:
        raise DateSyntaxError(exc)

epoch = datetime.datetime(1995, 7, 2, tzinfo=datetime.timezone.utc)

# ==============
# string formats
# ==============

def _read_string_formats():
    path = os.path.join(paths.datadir, 'string-formats')
    cp = configparser.ConfigParser(interpolation=None, default_section='')
    cp.read(path, encoding='ASCII')
    section = cp['formats']
    misc.check_sorted(section)
    return {
        name: frozenset(examples.split())
        for name, examples in section.items()
    }

string_formats = _read_string_formats()

# vim:ts=4 sts=4 sw=4 et
