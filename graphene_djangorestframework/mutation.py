from collections import OrderedDict

from django.shortcuts import get_object_or_404

from rest_framework.fields import SkipField

import graphene
import graphene.relay

from graphene.types import Argument
from graphene.types.mutation import Mutation, MutationOptions
from graphene.types.objecttype import yank_fields_from_attrs
from graphene.utils.str_converters import to_camel_case

from .types import ErrorType
from .fields import DjangoField
from .serializers import fields_for_serializer


class SerializerMutationOptions(MutationOptions):
    lookup_field = None
    model_class = None
    serializer_class = None
    node_class = graphene.relay.Node
    node_type = None
    partial = None
    registry = None


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
        throttle_classes=None,
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
            throttle_classes=throttle_classes,
        )


class SerializerBaseMutation(DjangoMutation):
    class Meta:
        abstract = True

    errors = graphene.List(
        ErrorType, description="May contain more than one error for same field."
    )

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        lookup_field=None,
        serializer_class=None,
        model_class=None,
        only_fields=(),
        exclude_fields=(),
        is_update=False,
        partial=False,
        **options
    ):

        if not serializer_class:
            raise Exception("serializer_class is required for SerializerMutation")

        serializer = serializer_class()
        if model_class is None:
            serializer_meta = getattr(serializer_class, "Meta", None)
            if serializer_meta:
                model_class = getattr(serializer_meta, "model", None)

        if is_update and not model_class:
            raise Exception("model_class is required for SerializerMutation")

        if lookup_field is None and model_class:
            lookup_field = model_class._meta.pk.name

        input_fields = fields_for_serializer(
            serializer,
            only_fields,
            exclude_fields,
            is_input=True,
            is_update=is_update,
            is_partial=partial,
        )
        output_fields = fields_for_serializer(
            serializer,
            only_fields,
            exclude_fields,
            is_input=False,
            is_update=is_update,
            is_partial=partial,
        )

        if is_update:
            input_fields = OrderedDict(
                id=graphene.ID(
                    required=True, description="ID of the object to update."
                ),
                **input_fields
            )

        _meta = SerializerMutationOptions(cls)
        _meta.lookup_field = lookup_field
        _meta.partial = partial
        _meta.serializer_class = serializer_class
        _meta.model_class = model_class
        _meta.fields = yank_fields_from_attrs(output_fields, _as=DjangoField, sort=False)

        input_fields = yank_fields_from_attrs(input_fields, _as=Argument, sort=False)
        super(SerializerBaseMutation, cls).__init_subclass_with_meta__(
            _meta=_meta, arguments=input_fields, **options
        )

    @classmethod
    def get_instance(cls, root, info, **input):
        return None

    @classmethod
    def get_serializer_kwargs(cls, root, info, **input):
        model_class = cls._meta.model_class
        partial = cls._meta.partial

        if model_class:
            instance = cls.get_instance(root, info, **input)

            return {
                "instance": instance,
                "data": input,
                "partial": partial,
                "context": {"request": info.context.get("request", None)},
            }

        return {
            "data": input,
            "partial": partial,
            "context": {"request": info.context.get("request", None)},
        }

    @classmethod
    def format_errors(cls, errors, field="", path=None):
        formatted_errors = []
        if path is None:
            path = []
        for key, value in errors.items():
            if isinstance(value, dict):
                formatted_errors += cls.format_errors(value, field=key + ".", path=path + [key])
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                for idx, error in enumerate(value):
                    idx_key = "{}[{}]".format(key, idx)
                    formatted_errors += cls.format_errors(error, field=idx_key + ".", path=path + [key, idx])
            else:
                formatted_errors.append(
                    ErrorType(field=field + to_camel_case(key), messages=value, path=path + [key])
                )

        return formatted_errors

    @classmethod
    def mutate(cls, root, info, **input):
        kwargs = cls.get_serializer_kwargs(root, info, **input)
        serializer = cls._meta.serializer_class(**kwargs)

        if serializer.is_valid():
            return cls.perform_mutate(serializer, info)
        else:
            errors = cls.format_errors(serializer.errors)

            return cls(errors=errors)

    @classmethod
    def perform_mutate(cls, serializer, info):
        obj = serializer.save()

        kwargs = {}
        for f, field in serializer.fields.items():
            if not field.write_only:
                try:
                    kwargs[f] = field.get_attribute(obj)
                except SkipField:
                    pass

        return cls(errors=None, **kwargs)


class SerializerCreateMutation(SerializerBaseMutation):
    class Meta:
        abstract = True


class SerializerUpdateMutation(SerializerBaseMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        lookup_field=None,
        serializer_class=None,
        model_class=None,
        only_fields=(),
        exclude_fields=(),
        partial=False,
        **options
    ):
        super(SerializerUpdateMutation, cls).__init_subclass_with_meta__(
            lookup_field=lookup_field,
            serializer_class=serializer_class,
            model_class=model_class,
            only_fields=only_fields,
            exclude_fields=exclude_fields,
            is_update=True,
            partial=partial,
            **options
        )

    @classmethod
    def get_instance(cls, root, info, **input):
        lookup_field = cls._meta.lookup_field

        if not input.get(lookup_field, None):
            raise Exception(
                'Invalid update operation. Input parameter "{}" required.'.format(
                    lookup_field
                )
            )

        model_class = cls._meta.model_class

        instance = get_object_or_404(model_class, **{lookup_field: input[lookup_field]})

        return instance
