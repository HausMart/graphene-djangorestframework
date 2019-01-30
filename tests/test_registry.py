from graphene_djangorestframework.registry import (
    get_global_registry,
    reset_global_registry,
)


def test_reset_global_registry():
    get_global_registry()

    from graphene_djangorestframework.registry import registry

    assert registry

    reset_global_registry()

    from graphene_djangorestframework.registry import registry

    assert not registry

