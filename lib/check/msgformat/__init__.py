# Copyright © 2014-2015 Jakub Wilk <jwilk@jwilk.net>
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
message format checks
'''

import abc

from lib import misc

class Checker(object, metaclass=abc.ABCMeta):

    def __init__(self, parent):
        self.parent = parent

    @abc.abstractproperty
    def backend(self):
        return

    def tag(self, tagname, *extra):
        return self.parent.tag(tagname, *extra)

    def check_message(self, ctx, message, flags):
        msgids = [message.msgid]
        if message.msgid_plural is not None:
            msgids += [message.msgid_plural]
        msgid_fmts = {}
        for i, s in enumerate(msgids):
            if ctx.is_template:
                fmt = self.check_string(ctx, message, s)
            else:
                try:
                    fmt = self.backend.FormatString(s)
                except self.backend.Error:
                    # If msgid isn't even a valid format string, then
                    # reporting errors against msgstr is not worth the trouble.
                    return
            if fmt is not None:
                msgid_fmts[i] = fmt
        if ctx.is_template and (len(msgid_fmts) == 2):
            self.check_args(
                message,
                'msgid_plural', msgid_fmts[1],
                'msgid', msgid_fmts[0],
                omitted_int_conv_ok=True,
            )
        self.check_msgids(message, msgid_fmts)
        if flags.fuzzy:
            return
        if ctx.encoding is None:
            return
        has_msgstr = bool(message.msgstr)
        has_msgstr_plural = any(message.msgstr_plural.values())
        strings = []
        if has_msgstr:
            d = misc.Namespace()
            d.src_loc = 'msgid'
            d.src_fmt = msgid_fmts.get(0)
            d.dst_loc = 'msgstr'
            d.dst_fmt = self.check_string(ctx, message, message.msgstr)
            d.omitted_int_conv_ok = False
            strings += [d]
        if has_msgstr_plural and ctx.plural_preimage:
            for i, s in sorted(message.msgstr_plural.items()):
                assert isinstance(i, int)
                d = misc.Namespace()
                msgid_fmt = msgid_fmts.get(0)
                msgid_plural_fmt = msgid_fmts.get(1)
                d.src_loc = 'msgid_plural'
                d.src_fmt = msgid_plural_fmt
                d.dst_loc = 'msgstr[{}]'.format(i)
                d.dst_fmt = self.check_string(ctx, message, s)
                if d.dst_fmt is None:
                    continue
                try:
                    preimage = ctx.plural_preimage[i]
                except KeyError:
                    # broken plural forms
                    continue
                preimage = [
                    x for x in preimage
                    if flags.range_min <= x <= flags.range_max
                ]
                # XXX In theory, the msgstr[] corresponding to n=1 should
                # not have more arguments than msgid. In practice, it's not
                # uncommon to see something like this:
                #
                # Plural-Forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2;
                #
                # msgid "one byte"
                # msgid_plural "%d bytes"
                # msgstr[0] "%d bajt"
                # msgstr[1] "%d bajta"
                # msgstr[2] "%d bajtova"
                #
                # Here %d in msgstr[0] cannot be omitted, because it is used
                # not only for n=1, but also for n=21, n=31, and so on.
                #
                # To be pedantically correct, one could use a different
                # Plural-Forms, such that there is a separate value for n=1.
                #
                # See also: https://bugs.debian.org/753946
                if preimage == [1]:
                    # FIXME: “preimage” is not necessarily complete.
                    # So it's theoretically possible that this msgstr[]
                    # corresponds to both n=1 and another n.
                    d.src_loc = 'msgid'
                    d.src_fmt = msgid_fmt
                    d.omitted_int_conv_ok = (
                        msgid_fmt is not None and
                        msgid_plural_fmt is not None and
                        len(msgid_fmt) == len(msgid_plural_fmt)
                        # FIXME: The length equality is a rather weak indicator
                        # that msgid and msgid_plural are equivalent.
                    )
                elif len(preimage) <= 1:
                    d.omitted_int_conv_ok = True
                elif len(preimage) == 2 and preimage[0] == 0:
                    # XXX In theory, the integer conversion should not be
                    # omitted in the msgstr[] corresponding to both n=0 and
                    # another n. In practice, it's sometimes obvious from
                    # context that the message will never be used for n=0.
                    d.omitted_int_conv_ok = True
                else:
                    d.omitted_int_conv_ok = False
                strings += [d]
        for d in strings:
            if d.dst_fmt is None:
                continue
            if d.src_fmt is None:
                continue
            assert d.src_loc is not None
            assert d.dst_loc is not None
            self.check_args(message,
                d.src_loc, d.src_fmt,
                d.dst_loc, d.dst_fmt,
                omitted_int_conv_ok=d.omitted_int_conv_ok,
            )

    def check_msgids(self, message, msgid_fmts):
        pass  # no coverage

    @abc.abstractmethod
    def check_string(self, ctx, message, s):
        pass  # no coverage

    @abc.abstractmethod
    def check_args(self, message, src_loc, src_fmt, dst_loc, dst_fmt, *, omitted_int_conv_ok=False):
        pass  # no coverage

__all__ = ['Checker']

# vim:ts=4 sts=4 sw=4 et
