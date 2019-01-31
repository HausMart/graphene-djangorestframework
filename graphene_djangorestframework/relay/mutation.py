from graphene.relay.mutation import ClientIDMutation

from ..fields import DjangoField


class DjangoClientIDMutation(ClientIDMutation):
    class Meta:
        abstract = True

    @classmethod
    def Field(
        cls,
        name=None,
        description=None,
        deprecation_reason=None,
        required=False,
        permission_classes=None,
    ):
        return DjangoField(
            cls._meta.output,
            args=cls._meta.arguments,
            resolver=cls._meta.resolver,
            name=name,
            description=description,
            deprecation_reason=deprecation_reason,
            required=required,
            permission_classes=permission_classes,
        )
