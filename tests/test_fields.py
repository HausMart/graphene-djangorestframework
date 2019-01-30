from django.utils.functional import SimpleLazyObject

from rest_framework.permissions import IsAuthenticated

import graphene

from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.fields import DjangoField, DjangoListField

from .app.models import Reporter


def test_django_field(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = DjangoField(ReporterType)

        def resolve_reporter(self, info):
            return SimpleLazyObject(lambda: Reporter(id=1))

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporter {
            id
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {"reporter": {"id": "1"}}


def test_django_list_field(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporters = DjangoListField(ReporterType)

        def resolve_reporters(self, info):
            return [SimpleLazyObject(lambda: Reporter(id=1))]

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporters {
            id
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {"reporters": [{"id": "1"}]}


def test_django_field_empty_permission_classes(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = DjangoField(ReporterType, permission_classes=[])

        def resolve_reporter(self, info):
            return SimpleLazyObject(lambda: Reporter(id=1))

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporter {
            id
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {"reporter": {"id": "1"}}


def test_django_field_inherited_permission_classes(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = DjangoField(ReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporter {
            id
          }
        }
    """
    result = schema.execute(
        query,
        context=info_with_context(
            resolver_permission_classes=[IsAuthenticated]
        ).context,
    )
    assert len(result.errors) == 1
    assert str(result.errors[0]) == "You do not have permission to perform this action."
    assert result.data == {"reporter": None}


def test_django_field_override_inherited_permission_classes(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = DjangoField(ReporterType, permission_classes=[])

        def resolve_reporter(self, info):
            return SimpleLazyObject(lambda: Reporter(id=1))

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporter {
            id
          }
        }
    """
    result = schema.execute(
        query,
        context=info_with_context(
            resolver_permission_classes=[IsAuthenticated]
        ).context,
    )
    assert not result.errors
    assert result.data == {"reporter": {"id": "1"}}


def test_django_field_with_permission_classes_anon(
    info_with_context, info_with_context_anon
):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = DjangoField(ReporterType, permission_classes=[IsAuthenticated])

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporter {
            id
          }
        }
    """
    result = schema.execute(
        query, context=info_with_context(user=info_with_context_anon()).context
    )
    assert len(result.errors) == 1
    assert str(result.errors[0]) == "You do not have permission to perform this action."
    assert result.data == {"reporter": None}


def test_django_field_with_permission_classes_allowed(
    info_with_context, info_with_context_user
):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = DjangoField(ReporterType, permission_classes=[IsAuthenticated])

        def resolve_reporter(self, info):
            return SimpleLazyObject(lambda: Reporter(id=1))

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporter {
            id
          }
        }
    """
    result = schema.execute(
        query, context=info_with_context(user=info_with_context_user()).context
    )
    assert not result.errors
    assert result.data == {"reporter": {"id": "1"}}


def test_django_list_field_with_permission_classes_anon(
    info_with_context, info_with_context_anon
):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporters = DjangoListField(ReporterType, permission_classes=[IsAuthenticated])

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporters {
            id
          }
        }
    """
    result = schema.execute(
        query, context=info_with_context(user=info_with_context_anon()).context
    )
    assert len(result.errors) == 1
    assert str(result.errors[0]) == "You do not have permission to perform this action."
    assert result.data == {"reporters": None}
