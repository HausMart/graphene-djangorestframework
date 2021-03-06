import pytest
from rest_framework.test import APIClient

from graphene_djangorestframework.registry import reset_global_registry, Registry


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(scope="function")
def reset_global_registry_after():
    yield True
    reset_global_registry()


@pytest.fixture(scope="function")
def registry():
    return Registry()


class _user(object):
    is_authenticated = True


class _anon(object):
    is_authenticated = False


class _request(object):
    def __init__(self, user=None):
        self.user = user
        self.META = {}


class _view(object):
    resolver_permission_classes = []

    def __init__(self, resolver_permission_classes=None):
        if resolver_permission_classes:
            self.resolver_permission_classes = resolver_permission_classes


class _info(object):
    def __init__(self, user=None, resolver_permission_classes=None):
        self.context = {
            "request": _request(user),
            "view": _view(resolver_permission_classes),
        }


@pytest.fixture
def info_with_context():
    return _info


@pytest.fixture
def info_with_context_anon():
    return _anon


@pytest.fixture
def info_with_context_user():
    return _user

