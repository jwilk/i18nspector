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
message format checks: C
'''

from lib import tags

from lib.check.msgformat import Checker as CheckerBase
from lib.check.msgrepr import message_repr

from lib.strformat import c as backend

class Checker(CheckerBase):

    backend = backend

    def check_msgids(self, message, msgid_fmts):
        if msgid_fmts.get(0) is not None:
            try:
                [[arg]] = msgid_fmts[0].arguments
            except ValueError:
                pass
            else:
                if arg.type == 'int *':
                    self.tag('qt-plural-format-mistaken-for-c-format', message_repr(message))

    def check_string(self, ctx, message, s):
        prefix = message_repr(message, template='{}:')
        fmt = None
        try:
            fmt = backend.FormatString(s)
        except backend.MissingArgument as exc:
            self.tag('c-format-string-error',
                prefix,
                tags.safestr(exc.message),
                tags.safestr('{1}$'.format(*exc.args)),
            )
        except backend.ArgumentTypeMismatch as exc:
            self.tag('c-format-string-error',
                prefix,
                tags.safestr(exc.message),
                tags.safestr('{1}$'.format(*exc.args)),
                tags.safestr(', '.join(sorted(x for x in exc.args[2]))),
            )
        except backend.FlagError as exc:
            [conv, flag] = exc.args  # pylint: disable=unbalanced-tuple-unpacking
            self.tag('c-format-string-error',
                prefix,
                tags.safestr(exc.message),
                flag, tags.safestr('in'), conv
            )
        except backend.Error as exc:
            self.tag('c-format-string-error',
                prefix,
                tags.safestr(exc.message),
                *exc.args[:1]
            )
        if fmt is None:
            return
        for warn in fmt.warnings:
            try:
                raise warn
            except backend.RedundantFlag as exc:
                if len(exc.args) == 2:
                    [s, *args] = exc.args
                else:
                    [s, a1, a2] = exc.args
                    if a1 == a2:
                        args = ['duplicate', a1]
                    else:
                        args = [a1, tags.safe_format('overridden by {}', a2)]
                args += ['in', s]
                self.tag('c-format-string-redundant-flag',
                    prefix,
                    *args
                )
            except backend.NonPortableConversion as exc:
                [s, c1, c2] = exc.args
                args = [c1, '=>', c2]
                if s != c1:
                    args += ['in', s]
                self.tag('c-format-string-non-portable-conversion',
                    prefix,
                    *args
                )
        return fmt

    def check_args(self, message, src_loc, src_fmt, dst_loc, dst_fmt, *, omitted_int_conv_ok=False):
        prefix = message_repr(message, template='{}:')
        src_args = src_fmt.arguments
        dst_args = dst_fmt.arguments
        if len(dst_args) > len(src_args):
            self.tag('c-format-string-excess-arguments', prefix,
                len(dst_args), tags.safestr('({})'.format(dst_loc)), '>',
                len(src_args), tags.safestr('({})'.format(src_loc)),
            )
        elif len(dst_args) < len(src_args):
            if omitted_int_conv_ok:
                n_args_omitted = len(src_args) - len(dst_args)
                omitted_int_conv_ok = src_fmt.get_last_integer_conversion(n=n_args_omitted)
            if not omitted_int_conv_ok:
                self.tag('c-format-string-missing-arguments', prefix,
                    len(dst_args), tags.safestr('({})'.format(dst_loc)), '<',
                    len(src_args), tags.safestr('({})'.format(src_loc)),
                )
        for src_arg, dst_arg in zip(src_args, dst_args):
            src_arg = src_arg[0]
            dst_arg = dst_arg[0]
            if src_arg.type != dst_arg.type:
                self.tag('c-format-string-argument-type-mismatch', prefix,
                    tags.safestr(dst_arg.type), tags.safestr('({})'.format(dst_loc)), '!=',
                    tags.safestr(src_arg.type), tags.safestr('({})'.format(src_loc)),
                )

__all__ = ['Checker']

# vim:ts=4 sts=4 sw=4 et
