from collections import OrderedDict

from django.core.exceptions import ImproperlyConfigured

from rest_framework import serializers

import graphene

from .utils import import_single_dispatch
from .registry import get_global_registry

singledispatch = import_single_dispatch()


class SerializerDjangoObjectTypeField(serializers.ReadOnlyField):
    def __init__(self, object_type, **kwargs):
        self.object_type = object_type
        kwargs["source"] = "*"
        super(SerializerDjangoObjectTypeField, self).__init__(**kwargs)


@singledispatch
def get_graphene_type_from_serializer_field(field):
    raise ImproperlyConfigured(
        "Don't know how to convert the serializer field %s (%s) "
        "to Graphene type" % (field, field.__class__)
    )


def convert_serializer_field(field, is_input=True, is_partial=False):
    """
    Converts a django rest frameworks field to a graphql field
    and marks the field as required if we are creating an input type
    and the field itself is required
    """
    graphql_type = get_graphene_type_from_serializer_field(field)

    if is_input and field.read_only:
        return None

    if not is_input and field.write_only:
        return None

    args = []
    kwargs = {
        "description": field.help_text,
        "required": is_input and field.required and not is_partial,
    }

    # if it is a tuple or a list it means that we are returning
    # the graphql type and the child type
    if isinstance(graphql_type, (list, tuple)):
        kwargs["of_type"] = graphql_type[1]
        graphql_type = graphql_type[0]

    if isinstance(field, serializers.ModelSerializer):
        if is_input:
            graphql_type = convert_serializer_to_input_type(field.__class__)
        else:
            global_registry = get_global_registry()
            field_model = field.Meta.model
            args = [global_registry.get_type_for_model(field_model)]
    elif isinstance(field, SerializerDjangoObjectTypeField):
        if is_input:
            raise ValueError(
                "SerializerDjangoObjectTypeField cannot be treated as an input."
            )
        else:
            args = [field.object_type]
    elif isinstance(field, serializers.ListSerializer):
        field = field.child
        if is_input:
            kwargs["of_type"] = convert_serializer_to_input_type(field.__class__)
        else:
            del kwargs["of_type"]
            global_registry = get_global_registry()
            field_model = field.Meta.model
            args = [global_registry.get_type_for_model(field_model)]

    return graphql_type(*args, **kwargs)


def convert_serializer_to_input_type(serializer_class):
    serializer = serializer_class()

    items = {}

    for name, field in serializer.fields.items():
        converted_field = convert_serializer_field(field)

        if converted_field:
            items[name] = converted_field

    return type(
        "{}Input".format(serializer.__class__.__name__),
        (graphene.InputObjectType,),
        items,
    )


def fields_for_serializer(
    serializer,
    only_fields,
    exclude_fields,
    is_input=False,
    is_update=False,
    is_partial=False,
):
    fields = OrderedDict()

    for name, field in serializer.fields.items():
        is_not_in_only = only_fields and name not in only_fields
        is_excluded = (
            name
            in exclude_fields  # or
            # name in already_created_fields
        )

        if is_not_in_only or is_excluded:
            continue

        converted_field = convert_serializer_field(
            field, is_input=is_input, is_partial=is_partial
        )

        if converted_field:
            if is_update and is_input and name == "id":
                raise Exception(
                    "Invalid SerializerUpdateMutation, serializer_class can only have a read_only id field."
                )
            fields[name] = converted_field
    return fields


@get_graphene_type_from_serializer_field.register(serializers.Field)
def convert_serializer_field_to_string(field):
    return graphene.String


@get_graphene_type_from_serializer_field.register(serializers.IntegerField)
def convert_serializer_field_to_int(field):
    return graphene.Int


@get_graphene_type_from_serializer_field.register(SerializerDjangoObjectTypeField)
def convert_serializer_field_to_field(field):
    return graphene.Field
