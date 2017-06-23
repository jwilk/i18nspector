'''
message format checks: Python's str.format()
'''

from lib import tags

from lib.check.msgformat import Checker as CheckerBase
from lib.check.msgrepr import message_repr

from lib.strformat import pybrace as backend

class Checker(CheckerBase):

    backend = backend

    def check_string(self, ctx, message, s):
        prefix = message_repr(message, template='{}:')
        fmt = None
        try:
            fmt = backend.FormatString(s)
        except backend.Error as exc:
            self.tag('python-brace-format-string-error',
                prefix,
                tags.safestr(exc.message),
                *exc.args[:1]
            )
        else:
            return fmt

    def check_args(self, message, src_loc, src_fmt, dst_loc, dst_fmt, *, omitted_int_conv_ok=False):
        def sort_key(item):
            return (isinstance(item, str), item)
        prefix = message_repr(message, template='{}:')
        src_args = src_fmt.argument_map
        dst_args = dst_fmt.argument_map
        for key in sorted(dst_args.keys() & src_args.keys(), key=sort_key):
            src_arg = src_args[key][0]
            dst_arg = dst_args[key][0]
            if not (src_arg.types & dst_arg.types):
                self.tag('python-brace-format-string-argument-type-mismatch', prefix,
                    tags.safestr(', '.join(dst_arg.types)), tags.safestr('({})'.format(dst_loc)), '!=',
                    tags.safestr(', '.join(src_arg.types)), tags.safestr('({})'.format(src_loc)),
                )
        for key in sorted(dst_args.keys() - src_args.keys(), key=sort_key):
            self.tag('python-brace-format-string-unknown-argument', prefix, key,
                tags.safestr('in'), tags.safestr(dst_loc),
                tags.safestr('but not in'), tags.safestr(src_loc),
            )
        missing_keys = src_args.keys() - dst_args.keys()
        if len(missing_keys) == 1 and omitted_int_conv_ok:
            [missing_key] = missing_keys
            if all('int' in arg.types for arg in src_args[missing_key]):
                missing_keys = set()
        for key in sorted(missing_keys):
            self.tag('python-brace-format-string-missing-argument', prefix, key,
                tags.safestr('not in'), tags.safestr(dst_loc),
                tags.safestr('while in'), tags.safestr(src_loc),
            )

# vim:ts=4 sts=4 sw=4 et
