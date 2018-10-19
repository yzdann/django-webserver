import os
import subprocess
import time

import pytest
from django.test import override_settings

from django_webserver.management.commands import pyuwsgi
from django_webserver.utils import WarmupFailure

try:
    from unittest import mock
except ImportError:
    import mock


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "django_webserver.tests.django_settings"
)
# make sure subprocess logs are flushed
os.environ["PYTHONUNBUFFERED"] = "1"


def run_server(name, *args):
    # timeout isn't supported in Python 2.7, do it the hard way...
    proc = subprocess.Popen(
        ["django-admin", name] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(1)
    proc.kill()
    return proc


def test_pyuwsgi():
    """Start a Django HTTP server and then kill it"""
    proc = run_server("pyuwsgi", "--http-socket=127.0.0.1:0")
    output = proc.communicate()[0].decode("utf-8")
    assert "uwsgi socket 0 bound to TCP address 127.0.0.1:" in output
    assert "WSGI app 0 (mountpoint='') ready in" in output


def test_gunicorn():
    proc = run_server("gunicorn", "--bind=127.0.0.1:0")
    output = proc.communicate()[0].decode("utf-8")
    assert "Listening at: http://127.0.0.1:" in output
    # :8000 is the default, ensure we aren't just seeing that
    assert "127.0.0.1:8000" not in output
    assert "Booting worker with pid:" in output


def test_waitress():
    proc = run_server("waitress", "--port=0", "--host=127.0.0.1")
    output = proc.communicate()[0].decode("utf-8")
    print(output)
    assert "Serving on http://localhost:" in output


def test_default_args():
    assert pyuwsgi.get_default_args() == [
        "--strict",
        "--need-app",
        "--module=django_webserver.tests.django_settings:application",
        "--static-map",
        "/static=/tmp/static",
    ]


@override_settings(PYUWSGI_ARGS=["--master", "--thunder-lock"])
def test_settings_args():
    assert pyuwsgi.get_default_args() == ["--master", "--thunder-lock"]


@mock.patch("django_webserver.base_command.get_internal_wsgi_application")
@mock.patch("pyuwsgi.run")
def test_warmup(m_run, m_wsgi):
    pyuwsgi.Command().run_from_argv([])
    m_wsgi.assert_called_once()
    m_run.assert_called_once()


@mock.patch("django_webserver.base_command.get_internal_wsgi_application")
@mock.patch("pyuwsgi.run")
@override_settings(WEBSERVER_WARMUP=False)
def test_no_warmup(m_run, m_wsgi):
    pyuwsgi.Command().run_from_argv([])
    m_wsgi.assert_not_called()
    m_run.assert_called_once()


@mock.patch("pyuwsgi.run")
@override_settings(WEBSERVER_WARMUP_HEALTHCHECK="/-/health/")
def test_healthcheck_ok(m_run):
    pyuwsgi.Command().run_from_argv([])
    m_run.assert_called_once()


@mock.patch("pyuwsgi.run")
@override_settings(WEBSERVER_WARMUP_HEALTHCHECK="/-/404/")
def test_healthcheck_fail(m_run):
    with pytest.raises(WarmupFailure):
        pyuwsgi.Command().run_from_argv([])


@mock.patch("pyuwsgi.run")
@override_settings(WEBSERVER_WARMUP_HEALTHCHECK="/-/health/", ALLOWED_HOSTS=[])
def test_healthcheck_no_allowed_hosts(m_run):
    pyuwsgi.Command().run_from_argv([])
    m_run.assert_called_once()
