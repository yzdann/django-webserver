import logging

from django.conf import settings
from django.test import RequestFactory

log = logging.getLogger(__name__)


class WarmupFailure(Exception):
    pass


def wsgi_healthcheck(app, url, ok_status=200):
    try:
        headers = {"HTTP_HOST": settings.ALLOWED_HOSTS[0]}
    except (AttributeError, IndexError):
        headers = {}
    warmup = app.get_response(RequestFactory().get(url, **headers))
    if warmup.status_code != ok_status:
        raise WarmupFailure(
            "WSGI warmup using endpoint {} responded with a {}.".format(
                url, warmup.status_code
            )
        )


def wsgi_app_name():
    return ":".join(settings.WSGI_APPLICATION.rsplit(".", 1))
