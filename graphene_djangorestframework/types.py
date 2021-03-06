from textwrap import dedent
from collections import OrderedDict

from django.utils.functional import SimpleLazyObject

import graphene

from graphene import Field
from graphene.relay import Node
from graphene.types.objecttype import ObjectType, ObjectTypeOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene.types.unmountedtype import UnmountedType


from .relay.connection import DjangoConnection
from .converter import convert_django_field_with_choices
from .registry import Registry, get_global_registry
from .utils import (
    DJANGO_FILTER_INSTALLED,
    get_model_fields,
    is_valid_django_model,
    maybe_queryset,
)


def construct_fields(model, registry, only_fields, exclude_fields):
    _model_fields = get_model_fields(model)

    fields = OrderedDict()
    for name, field in _model_fields:
        is_not_in_only = only_fields and name not in only_fields
        # is_already_created = name in options.fields
        is_excluded = name in exclude_fields  # or is_already_created
        # https://docs.djangoproject.com/en/1.10/ref/models/fields/#django.db.models.ForeignKey.related_query_name
        is_no_backref = str(name).endswith("+")
        if is_not_in_only or is_excluded or is_no_backref:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we exclude this field in exclude_fields.
            # Or when there is no back reference.
            continue
        converted = convert_django_field_with_choices(field, registry)
        fields[name] = converted

    return fields


class DjangoObjectTypeOptions(ObjectTypeOptions):
    model = None
    id_field = None
    registry = None
    connection = None

    filter_fields = ()


class DjangoObjectType(ObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model=None,
        id_field=None,
        registry=None,
        skip_registry=False,
        only_fields=(),
        exclude_fields=(),
        filter_fields=None,
        connection=None,
        connection_class=None,
        use_connection=None,
        interfaces=(),
        _meta=None,
        **options
    ):
        assert is_valid_django_model(model), (
            'You need to pass a valid Django Model in {}.Meta, received "{}".'
        ).format(cls.__name__, model)

        if not registry:
            registry = get_global_registry()

        assert isinstance(registry, Registry), (
            "The attribute registry in {} needs to be an instance of "
            'Registry, received "{}".'
        ).format(cls.__name__, registry)

        if not DJANGO_FILTER_INSTALLED and filter_fields:
            raise Exception("Can only set filter_fields if Django-Filter is installed")

        django_fields = yank_fields_from_attrs(
            construct_fields(model, registry, only_fields, exclude_fields), _as=Field
        )

        if use_connection is None and interfaces:
            use_connection = any(
                (issubclass(interface, Node) for interface in interfaces)
            )

        if use_connection and not connection:
            # We create the connection automatically
            if not connection_class:
                connection_class = DjangoConnection

            connection = connection_class.create_type(
                "{}Connection".format(cls.__name__), node=cls
            )

        if connection is not None:
            assert issubclass(connection, DjangoConnection), (
                "The connection must be a DjangoConnection. Received {}"
            ).format(connection.__name__)

        if not id_field:
            id_field = "pk"

        if not _meta:
            _meta = DjangoObjectTypeOptions(cls)

        _meta.model = model
        _meta.id_field = id_field
        _meta.registry = registry
        _meta.filter_fields = filter_fields
        _meta.fields = django_fields
        _meta.connection = connection

        super(DjangoObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, interfaces=interfaces, **options
        )

        if not skip_registry:
            registry.register(cls)

    def resolve_id(self, info):
        return getattr(self, info.parent_type.graphene_type._meta.id_field)

    @classmethod
    def is_type_of(cls, root, info):
        if isinstance(root, SimpleLazyObject):
            root._setup()
            root = root._wrapped
        if isinstance(root, cls):
            return True
        if not is_valid_django_model(type(root)):
            raise Exception(('Received incompatible instance "{}".').format(root))

        model = root._meta.model._meta.concrete_model
        return model == cls._meta.model

    @classmethod
    def get_node(cls, info, id):
        get_queryset_attr = getattr(cls, "get_queryset", None)
        if callable(get_queryset_attr):
            queryset_or_manager = get_queryset_attr
        else:
            queryset_or_manager = cls._meta.model._default_manager

        try:
            return maybe_queryset(queryset_or_manager, info).get(**{cls._meta.id_field: id})
        except cls._meta.model.DoesNotExist:
            return None


class ErrorType(graphene.ObjectType):
    field = graphene.String(
        description=dedent(
            """Name of a field that caused the error. A value of
        `null` indicates that the error isn't associated with a particular
        field."""
        ),
        required=False,
    )
    messages = graphene.List(
        graphene.NonNull(graphene.String),
        description="The error messages.",
        required=True,
    )
    path = graphene.List(
        graphene.NonNull(graphene.String),
        description="""Path to the name of a field that caused the error.
        A value of `null` indicates that the error isn't associated with a
        particular field.""",
        required=False,
    )


class DictType(UnmountedType):
    key = graphene.String()
    value = graphene.String()
