import warnings

from functools import partial

from graphene.types import Field, List

from rest_framework.exceptions import PermissionDenied

from .utils import maybe_queryset


def check_permission_classes(info, field, permission_classes):
    if permission_classes is None:
        if hasattr(info, "context") and info.context and info.context.get("view", None):
            permission_classes = info.context.get("view").resolver_permission_classes
        else:
            warnings.warn(
                UserWarning(
                    "{} should not be called without context.".format(field.__name__)
                )
            )

    if permission_classes is not None:
        for permission in [p() for p in permission_classes]:
            if not permission.has_permission(
                info.context.get("request"), info.context.get("view")
            ):
                raise PermissionDenied(detail=getattr(permission, "message", None))


class DjangoField(Field):
    def __init__(self, *args, **kwargs):
        self.permission_classes = kwargs.pop("permission_classes", None)
        super(DjangoField, self).__init__(*args, **kwargs)

    @classmethod
    def field_resolver(
        cls, resolver, root, info, permission_classes=None, *args, **kwargs
    ):
        check_permission_classes(info, cls, permission_classes)

        return resolver(root, info, *args, **kwargs)

    def get_resolver(self, parent_resolver):
        return partial(
            self.field_resolver,
            self.resolver or parent_resolver,
            permission_classes=self.permission_classes,
        )


class DjangoListField(Field):
    def __init__(self, _type, *args, **kwargs):
        self.permission_classes = kwargs.pop("permission_classes", None)
        super(DjangoListField, self).__init__(List(_type), *args, **kwargs)

    @property
    def model(self):
        return self.type.of_type._meta.node._meta.model

    @classmethod
    def list_resolver(cls, resolver, root, info, permission_classes=None, **args):
        check_permission_classes(info, cls, permission_classes)

        return maybe_queryset(resolver(root, info, **args))

    def get_resolver(self, parent_resolver):
        return partial(
            self.list_resolver,
            parent_resolver,
            permission_classes=self.permission_classes,
        )
