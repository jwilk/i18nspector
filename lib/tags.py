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
tag support
'''

import configparser
import functools
import os
import re

from lib import misc
from lib import paths
from lib import terminal

@functools.total_ordering
class OrderedObject():

    _parent = None

    def __init__(self, name, value):
        assert self._parent is not None
        self._name = name
        self._value = value

    # pylint: disable=protected-access

    def __lt__(self, other):
        if not isinstance(other, OrderedObject):
            return NotImplemented
        if self._parent is not other._parent:
            return NotImplemented
        return self._value < other._value

    def __eq__(self, other):
        if not isinstance(other, OrderedObject):
            return NotImplemented
        if self._parent is not other._parent:
            return NotImplemented
        return self._value == other._value

    # pylint: enable=protected-access

    def __hash__(self):
        return hash(self._value)

    def __str__(self):
        return str(self._name)

class OrderedGroup():

    def __init__(self, name, *items):
        self._child_type = ct = type(name, (OrderedObject,), dict(_parent=self))
        self._objects = dict(
            (name, ct(name, value))
            for value, name in enumerate(items)
        )

    def __getitem__(self, name):
        return self._objects[name]

severities = OrderedGroup('Severity',
    'pedantic',
    'wishlist',
    'minor',
    'normal',
    'important',
    'serious'
)

certainties = OrderedGroup('Certainty',
    'wild-guess',
    'possible',
    'certain',
)

class InvalidSeverity(misc.DataIntegrityError):
    pass

class InvalidCertainty(misc.DataIntegrityError):
    pass

class UnknownField(misc.DataIntegrityError):
    pass

_is_safe = re.compile(r'\A[A-Za-z0-9_.!<>=-]+\Z').match

class safestr(str):
    pass

def _escape(s):
    if isinstance(s, safestr):
        return s
    if isinstance(s, bytes):
        return repr(s)[1:]
    s = str(s)
    if s == '':
        return '(empty string)'
    elif _is_safe(s):
        return s
    else:
        return repr(s)

def safe_format(template, *args, **kwargs):
    args = [_escape(s) for s in args]
    kwargs = {k: _escape(v) for k, v in kwargs.items()}
    return safestr(template.format(*args, **kwargs))

class Tag():

    def __init__(self, **kwargs):
        self.description = None
        self.references = []
        for k, v in kwargs.items():
            try:
                getattr(self, '_set_' + k)(v)
            except AttributeError:
                raise UnknownField(k)
        type({self.name, self.severity, self.certainty})

    # pylint: disable=attribute-defined-outside-init

    def _set_name(self, value):
        self.name = value

    def _set_severity(self, value):
        try:
            self.severity = severities[value]
        except KeyError as exc:
            [key] = exc.args
            raise InvalidSeverity(key)

    def _set_certainty(self, value):
        try:
            self.certainty = certainties[value]
        except KeyError as exc:
            [key] = exc.args
            raise InvalidCertainty(key)

    # pylint: enable=attribute-defined-outside-init

    _strip_leading_dot = functools.partial(
        re.compile('^[.]', re.MULTILINE).sub,
        ''
    )

    @classmethod
    def _parse_multiline(cls, value):
        for s in value.splitlines():
            if not s or s.isspace():
                continue
            yield cls._strip_leading_dot(s)

    def _set_description(self, value):
        value = '\n'.join(self._parse_multiline(value))
        self.description = value

    def _set_references(self, value):
        self.references += self._parse_multiline(value)

    def get_colors(self):
        prio = self.get_priority()
        n = dict(
            P=terminal.colors.green,
            I=terminal.colors.cyan,
            W=terminal.colors.yellow,
            E=terminal.colors.red,
        )[prio]
        return (
            terminal.attr_fg(n),
            terminal.attr_reset()
        )

    def get_priority(self):
        s = self.severity
        S = severities
        c = self.certainty
        C = certainties
        return {
            S['pedantic']: 'P',
            S['wishlist']: 'I',
            S['minor']: 'IW'[c >= C['certain']],
            S['normal']: 'IW'[c >= C['possible']],
            S['important']: 'WE'[c >= C['possible']],
            S['serious']: 'E',
        }[s]

    def format(self, target, *extra, color=False):
        if color:
            color_on, color_off = self.get_colors()
        else:
            color_on = color_off = ''
        s = '{prio}: {target}: {on}{tag}{off}'.format(
            prio=self.get_priority(),
            target=target,
            tag=self.name,
            on=color_on,
            off=color_off,
        )
        if extra:
            s += ' ' + ' '.join(map(_escape, extra))
        return s

def _read_tags():
    path = os.path.join(paths.datadir, 'tags')
    cp = configparser.ConfigParser(interpolation=None, default_section='')
    cp.read(path, encoding='UTF-8')
    misc.check_sorted(cp)
    tags = {}
    for tagname, section in cp.items():
        if not tagname:
            continue
        kwargs = dict(section.items())
        kwargs['name'] = tagname
        tags[tagname] = Tag(**kwargs)
    return tags

_tags = _read_tags()

def tag_exists(tagname):
    return tagname in _tags

def iter_tags():
    return (tag for _, tag in sorted(_tags.items()))

def get_tag(tagname):
    return _tags[tagname]

# vim:ts=4 sts=4 sw=4 et
