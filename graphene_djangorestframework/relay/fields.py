from functools import partial
from promise import Promise

from django.db.models.query import QuerySet

from graphene.relay import ConnectionField, PageInfo, Connection
from graphql_relay.connection.arrayconnection import connection_from_list_slice

from ..utils import maybe_queryset
from ..settings import graphene_settings
from ..fields import check_permission_classes, check_throttle_classes


class DjangoConnectionField(ConnectionField):
    def __init__(self, *args, **kwargs):
        self.on = kwargs.pop("on", False)
        self.max_limit = kwargs.pop(
            "max_limit", graphene_settings.RELAY_CONNECTION_MAX_LIMIT
        )
        self.enforce_first_or_last = kwargs.pop(
            "enforce_first_or_last",
            graphene_settings.RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST,
        )
        self.permission_classes = kwargs.pop("permission_classes", None)
        self.throttle_classes = kwargs.pop("throttle_classes", None)
        super(DjangoConnectionField, self).__init__(*args, **kwargs)

    @property
    def type(self):
        from ..types import DjangoObjectType

        _type = super(ConnectionField, self).type

        if issubclass(_type, Connection):
            return _type

        assert issubclass(
            _type, DjangoObjectType
        ), "DjangoConnectionField only accepts DjangoObjectType and Connection types"

        assert _type._meta.connection, "The type {} doesn't have a connection".format(
            _type.__name__
        )
        return _type._meta.connection

    @property
    def node_type(self):
        return self.type._meta.node

    @property
    def model(self):
        return getattr(self.node_type._meta, 'model', None)

    def get_manager_or_queryset(self):
        if self.model is None:
            return None

        get_queryset_attr = getattr(self.node_type, "get_queryset", None)
        if self.on:
            return getattr(self.model, self.on)
        elif callable(get_queryset_attr):
            return get_queryset_attr
        else:
            return self.model._default_manager

    @classmethod
    def merge_querysets(cls, default_queryset, queryset):
        if default_queryset.query.distinct and not queryset.query.distinct:
            queryset = queryset.distinct()
        elif queryset.query.distinct and not default_queryset.query.distinct:
            default_queryset = default_queryset.distinct()
        return queryset & default_queryset

    @classmethod
    def resolve_connection(cls, connection, default_manager, args, info, iterable):
        if iterable is None:
            iterable = default_manager
        iterable = maybe_queryset(iterable, info)
        if isinstance(iterable, QuerySet):
            if iterable is not default_manager:
                default_queryset = maybe_queryset(default_manager, info)
                iterable = cls.merge_querysets(default_queryset, iterable)
            _len = iterable.count()
        else:
            _len = len(iterable)
        connection = connection_from_list_slice(
            iterable,
            args,
            slice_start=0,
            list_length=_len,
            list_slice_length=_len,
            connection_type=connection,
            edge_type=connection.Edge,
            pageinfo_type=PageInfo,
        )
        connection.iterable = iterable
        connection.length = _len
        connection.total_count = _len
        return connection

    @classmethod
    def connection_resolver(
        cls,
        resolver,
        connection,
        default_manager,
        max_limit,
        enforce_first_or_last,
        permission_classes,
        throttle_classes,
        root,
        info,
        **args
    ):
        check_permission_classes(info, cls, permission_classes)
        check_throttle_classes(info, cls, throttle_classes)

        first = args.get("first")
        last = args.get("last")

        if enforce_first_or_last:
            assert first or last, (
                "You must provide a `first` or `last` value to properly paginate the `{}` connection."
            ).format(info.field_name)

        if max_limit:
            if first:
                assert first <= max_limit, (
                    "Requesting {} records on the `{}` connection exceeds the `first` limit of {} records."
                ).format(first, info.field_name, max_limit)
                args["first"] = min(first, max_limit)

            if last:
                assert last <= max_limit, (
                    "Requesting {} records on the `{}` connection exceeds the `last` limit of {} records."
                ).format(last, info.field_name, max_limit)
                args["last"] = min(last, max_limit)

        iterable = resolver(root, info, **args)
        on_resolve = partial(
            cls.resolve_connection, connection, default_manager, args, info
        )

        if Promise.is_thenable(iterable):
            return Promise.resolve(iterable).then(on_resolve)

        return on_resolve(iterable)

    def get_resolver(self, parent_resolver):
        return partial(
            self.connection_resolver,
            parent_resolver,
            self.type,
            self.get_manager_or_queryset(),
            self.max_limit,
            self.enforce_first_or_last,
            self.permission_classes,
            self.throttle_classes,
        )
