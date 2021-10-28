
import os
import tempfile


def pytest_sessionstart(session):
    envvar = 'XDG_CACHE_HOME'
    old_xdg_cache_home = os.environ.get(envvar, None)
    xdg_temp_dir = tempfile.TemporaryDirectory(prefix='i18nspector.tests.')  # pylint: disable=consider-using-with
    os.environ[envvar] = xdg_temp_dir.name

    def cleanup():
        xdg_temp_dir.cleanup()
        if old_xdg_cache_home is None:
            del os.environ[envvar]
        else:
            os.environ[envvar] = old_xdg_cache_home

    session.config.add_cleanup(cleanup)
