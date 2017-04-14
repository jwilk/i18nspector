# Copyright © 2015 Jakub Wilk <jwilk@jwilk.net>
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
message format checks: Python's %-formatting
'''

from lib import tags

from lib.check.msgformat import Checker as CheckerBase
from lib.check.msgrepr import message_repr

from lib.strformat import python as backend

class Checker(CheckerBase):

    backend = backend

    def check_string(self, ctx, message, s):
        prefix = message_repr(message, template='{}:')
        fmt = None
        try:
            fmt = backend.FormatString(s)
        except backend.ArgumentTypeMismatch as exc:
            [s, key, types] = exc.args  # pylint: disable=unbalanced-tuple-unpacking
            self.tag('python-format-string-error',
                prefix,
                tags.safestr(exc.message),
                tags.safestr(key),
                tags.safestr(', '.join(sorted(x for x in types))),
            )
        except backend.Error as exc:
            self.tag('python-format-string-error',
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
                self.tag('python-format-string-redundant-flag',
                    prefix,
                    *args
                )
            except backend.RedundantPrecision as exc:
                [s, a] = exc.args
                self.tag('python-format-string-redundant-precision',
                    prefix,
                    a, 'in', s
                )
            except backend.RedundantLength as exc:
                [s, a] = exc.args
                self.tag('python-format-string-redundant-length',
                    prefix,
                    a, 'in', s
                )
            except backend.ObsoleteConversion as exc:
                [s, c1, c2] = exc.args
                args = [c1, '=>', c2]
                if s != c1:
                    args += ['in', s]
                self.tag('python-format-string-obsolete-conversion',
                    prefix,
                    *args
                )
        if ctx.is_template:
            if len(fmt.seq_conversions) > 1:
                self.tag('python-format-string-multiple-unnamed-arguments',
                    message_repr(message)
                )
            elif len(fmt.seq_conversions) == 1:
                arg_for_plural = (
                    message.msgid_plural is not None and
                    fmt.seq_conversions[0].type == 'int'
                )
                if arg_for_plural:
                    self.tag('python-format-string-unnamed-plural-argument',
                        message_repr(message)
                    )
        return fmt

    def check_args(self, message, src_loc, src_fmt, dst_loc, dst_fmt, *, omitted_int_conv_ok=False):
        prefix = message_repr(message, template='{}:')
        # unnamed arguments:
        src_args = src_fmt.seq_arguments
        dst_args = dst_fmt.seq_arguments
        if len(dst_args) != len(src_args):
            self.tag('python-format-string-argument-number-mismatch', prefix,
                len(dst_args), tags.safestr('({})'.format(dst_loc)), '!=',
                len(src_args), tags.safestr('({})'.format(src_loc)),
            )
        for src_arg, dst_arg in zip(src_args, dst_args):
            if src_arg.type != dst_arg.type:
                self.tag('python-format-string-argument-type-mismatch', prefix,
                    tags.safestr(dst_arg.type), tags.safestr('({})'.format(dst_loc)), '!=',
                    tags.safestr(src_arg.type), tags.safestr('({})'.format(src_loc)),
                )
        # named arguments:
        src_args = src_fmt.map_arguments
        dst_args = dst_fmt.map_arguments
        for key in sorted(dst_args.keys() & src_args.keys()):
            src_arg = src_args[key][0]
            dst_arg = dst_args[key][0]
            if src_arg.type != dst_arg.type:
                self.tag('python-format-string-argument-type-mismatch', prefix,
                    tags.safestr(dst_arg.type), tags.safestr('({})'.format(dst_loc)), '!=',
                    tags.safestr(src_arg.type), tags.safestr('({})'.format(src_loc)),
                )
        for key in sorted(dst_args.keys() - src_args.keys()):
            self.tag('python-format-string-unknown-argument', prefix, key,
                tags.safestr('in'), tags.safestr(dst_loc),
                tags.safestr('but not in'), tags.safestr(src_loc),
            )
        missing_keys = src_args.keys() - dst_args.keys()
        if len(missing_keys) == 1 and omitted_int_conv_ok:
            [missing_key] = missing_keys
            if all(arg.type == 'int' for arg in src_args[missing_key]):
                missing_keys = set()
        for key in sorted(missing_keys):
            self.tag('python-format-string-missing-argument', prefix, key,
                tags.safestr('not in'), tags.safestr(dst_loc),
                tags.safestr('while in'), tags.safestr(src_loc),
            )

__all__ = ['Checker']

# vim:ts=4 sts=4 sw=4 et
