from collections import OrderedDict

from django.http import Http404

from rest_framework.fields import SkipField

import graphene

from graphene.types import InputField, Field
from graphene.relay.mutation import ClientIDMutation
from graphene.types.objecttype import yank_fields_from_attrs
from graphene.utils.str_converters import to_camel_case

from ..registry import get_global_registry
from ..fields import DjangoField
from ..types import ErrorType
from ..mutation import SerializerMutationOptions
from ..serializers import fields_for_serializer

global_registry = get_global_registry()


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
        throttle_classes=None,
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
            throttle_classes=throttle_classes,
        )


class SerializerBaseClientIDMutation(DjangoClientIDMutation):
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
        node_class=None,
        only_fields=(),
        exclude_fields=(),
        is_update=False,
        id_input_field=None,
        partial=False,
        registry=None,
        **options
    ):

        if not serializer_class:
            raise Exception(
                "serializer_class is required for SerializerClientIDMutation"
            )

        serializer = serializer_class()
        if model_class is None:
            serializer_meta = getattr(serializer_class, "Meta", None)
            if serializer_meta:
                model_class = getattr(serializer_meta, "model", None)

        if node_class and not issubclass(node_class, graphene.relay.Node):
            raise Exception("node_class must be a subclass of relay.Node")

        if is_update and not model_class:
            raise Exception("model_class is required for SerializerClientIDMutation")

        if lookup_field is None and model_class:
            lookup_field = model_class._meta.pk.name

        input_fields = fields_for_serializer(
            serializer,
            only_fields,
            exclude_fields,
            registry,
            is_input=True,
            is_update=is_update,
            is_partial=partial,
        )
        output_fields = fields_for_serializer(
            serializer,
            only_fields,
            exclude_fields,
            registry,
            is_input=False,
            is_update=is_update,
            is_partial=partial,
        )

        if is_update and id_input_field:
            input_fields = OrderedDict(
                **{
                    id_input_field: graphene.ID(
                        required=True, description="ID of the object to update."
                    )
                },
                **input_fields
            )

        _meta = SerializerMutationOptions(cls)
        _meta.lookup_field = lookup_field
        _meta.id_input_field = id_input_field
        _meta.partial = partial
        _meta.serializer_class = serializer_class
        _meta.model_class = model_class
        _meta.registry = registry
        _meta.fields = yank_fields_from_attrs(output_fields, _as=Field)

        if node_class:
            _meta.node_class = node_class

        input_fields = yank_fields_from_attrs(input_fields, _as=InputField)
        super(SerializerBaseClientIDMutation, cls).__init_subclass_with_meta__(
            _meta=_meta, input_fields=input_fields, **options
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
                "context": {
                    "request": info.context.get("request", None),
                    "info": info,
                    "mutation": cls,
                },
            }

        return {
            "data": input,
            "partial": partial,
            "context": {
                "request": info.context.get("request", None),
                "info": info,
                "mutation": cls,
            },
        }

    @classmethod
    def format_errors(cls, errors, field="", path=None):
        formatted_errors = []
        if path is None:
            path = []
        for key, value in errors.items():
            key = to_camel_case(str(key))
            if isinstance(value, dict):
                formatted_errors += cls.format_errors(
                    value, field=key + ".", path=path + [key]
                )
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                for idx, error in enumerate(value):
                    idx_key = "{}[{}]".format(key, idx)
                    formatted_errors += cls.format_errors(
                        error, field=idx_key + ".", path=path + [key, idx]
                    )
            else:
                formatted_errors.append(
                    ErrorType(field=field + key, messages=value, path=path + [key])
                )

        return formatted_errors

    @classmethod
    def handle_serializer_errors(cls, serializer):
        errors = cls.format_errors(serializer.errors)

        return cls(errors=errors)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        kwargs = cls.get_serializer_kwargs(root, info, **input)
        serializer = cls._meta.serializer_class(**kwargs)

        if serializer.is_valid():
            return cls.perform_mutate(serializer, info)
        else:
            return cls.handle_serializer_errors(serializer)

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

        value = cls(errors=None, **kwargs)

        return value


class SerializerClientIDCreateMutation(SerializerBaseClientIDMutation):
    class Meta:
        abstract = True


class SerializerClientIDUpdateMutation(SerializerBaseClientIDMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        lookup_field=None,
        serializer_class=None,
        model_class=None,
        node_class=None,
        only_fields=(),
        exclude_fields=(),
        id_input_field="id",
        partial=False,
        **options
    ):
        super(SerializerClientIDUpdateMutation, cls).__init_subclass_with_meta__(
            lookup_field=lookup_field,
            serializer_class=serializer_class,
            model_class=model_class,
            node_class=node_class,
            only_fields=only_fields,
            exclude_fields=exclude_fields,
            is_update=True,
            id_input_field=id_input_field,
            partial=partial,
            **options
        )

    @classmethod
    def get_instance(cls, root, info, **input):
        id_input_field = cls._meta.id_input_field

        if not input.get(id_input_field):
            raise Exception(
                'Invalid update operation. Input parameter "{}" required.'.format(
                    id_input_field
                )
            )

        model_class = cls._meta.model_class
        node_class = cls._meta.node_class
        registry = cls._meta.registry if cls._meta.registry else global_registry

        model_type = registry.get_type_for_model(model_class)
        instance = node_class.get_node_from_global_id(
            info, input.get(id_input_field), model_type
        )

        if instance is None:
            raise Http404(
                "No %s matches the given query." % model_class._meta.object_name
            )

        return instance
