import inspect
import os.path

from .conftest import tagstring, etags_from_tagstring, assert_emit_tags
from .. import tools


def this():
    '''
    Return function that called this function. (Hopefully!)
    '''
    return globals()[inspect.stack()[1][0].f_code.co_name]

@tagstring('''
E: os-error No such file or directory
''')
def test_os_error_no_such_file():
    with tools.temporary_directory() as tmpdir:
        path = os.path.join(tmpdir, 'nonexistent.po')
        expected = etags_from_tagstring(this(), path)
        assert_emit_tags(path, expected)

@tagstring('''
E: os-error Permission denied
''')
def test_os_error_permission_denied():
    if os.getuid() == 0:
        raise unittest.SkipTest('this test must not be run as root')
    with tools.temporary_directory() as tmpdir:
        path = os.path.join(tmpdir, 'denied.po')
        with open(path, 'wb'):
            pass
        os.chmod(path, 0)
        expected = etags_from_tagstring(this(), path)
        assert_emit_tags(path, expected)
