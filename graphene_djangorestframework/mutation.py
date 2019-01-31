import graphene

from graphene.types.mutation import Mutation

from .types import ErrorType
from .fields import DjangoField


class DjangoMutation(Mutation):
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
            description=description or cls._meta.description,
            deprecation_reason=deprecation_reason,
            required=required,
            permission_classes=permission_classes,
        )


# class SerializerBaseMutation(DjangoMutation):
#     class Meta:
#         abstract = True

#     errors = graphene.List(
#         ErrorType, description="May contain more than one error for same field."
#     )
