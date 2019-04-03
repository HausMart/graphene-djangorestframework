import pytest

from django.utils.functional import SimpleLazyObject

from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle

from graphql_relay.node.node import to_global_id

import graphene

from graphene import relay

from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.relay.node import DjangoNode
from graphene_djangorestframework.relay.fields import DjangoConnectionField


from ..app.models import Reporter


def test_django_connection_field(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            interfaces = (relay.Node,)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporters = DjangoConnectionField(ReporterType)

        def resolve_reporters(self, info):
            return [SimpleLazyObject(lambda: Reporter(id=1))]

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporters {
            edges {
              node {
                id
              }
            }
            totalCount
            pageInfo {
                hasNextPage
            }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {
        "reporters": {
            "edges": [{"node": {"id": "UmVwb3J0ZXJUeXBlOjE="}}],
            "totalCount": 1,
            "pageInfo": {"hasNextPage": False},
        }
    }


def test_django_field_with_permission_classes(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            interfaces = (relay.Node,)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporters = DjangoConnectionField(
            ReporterType, permission_classes=[IsAuthenticated]
        )

        def resolve_reporters(self, info):
            return [SimpleLazyObject(lambda: Reporter(id=1))]

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporters {
            edges {
              node {
                id
              }
            }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == "You do not have permission to perform this action."
    assert result.data == {"reporters": None}


def test_django_field_with_throttle_classes(info_with_context, info_with_context_anon):
    class TestThrottle(UserRateThrottle):
        scope = "test_django_field_with_throttle_classes"

        def get_rate(self):
            return "1/minute"

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            interfaces = (relay.Node,)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporters = DjangoConnectionField(ReporterType, throttle_classes=[TestThrottle])

        def resolve_reporters(self, info):
            return [SimpleLazyObject(lambda: Reporter(id=1))]

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporters {
            totalCount
          }
        }
    """

    # First request. Not throttled.
    result = schema.execute(
        query, context=info_with_context(user=info_with_context_anon()).context
    )
    assert result.errors is None
    assert result.data == {"reporters": {"totalCount": 1}}

    # Second request. Throttled.
    result = schema.execute(
        query, context=info_with_context(user=info_with_context_anon()).context
    )
    assert len(result.errors) == 1
    assert (
        str(result.errors[0])
        == "Request was throttled. Expected available in 60 seconds."
    )
    assert result.data == {"reporters": None}


@pytest.mark.django_db
def test_django_object_type_get_node_with_manager(info_with_context):
    r1 = Reporter.objects.create(
        first_name="r1", last_name="r1", email="reportername@test.com"
    )

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            interfaces = (DjangoNode,)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = DjangoNode.Field(ReporterType)

    r1_id = to_global_id("ReporterType", r1.id)

    schema = graphene.Schema(query=Query)
    query = """
        query Reporter($id: ID!) {
          reporter(id: $id) {
            id
          }
        }
    """

    # Success.
    result = schema.execute(
        query, context=info_with_context().context, variables={"id": r1_id}
    )
    assert not result.errors
    assert result.data == {"reporter": {"id": r1_id}}


@pytest.mark.django_db
def test_django_object_type_get_node_with_queryset(info_with_context):
    r1 = Reporter.objects.create(
        first_name="r1", last_name="r1", email="reportername@test.com"
    )
    r2 = Reporter.objects.create(
        first_name="r2", last_name="r2", email="reportername@test.com"
    )

    class ReporterType(DjangoObjectType):
        @classmethod
        def get_queryset(cls, info):
            return Reporter.objects.filter(pk=r1.pk)

        class Meta:
            model = Reporter
            only_fields = ("id",)
            interfaces = (DjangoNode,)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = DjangoNode.Field(ReporterType)

    r1_id = to_global_id("ReporterType", r1.id)
    r2_id = to_global_id("ReporterType", r2.id)

    schema = graphene.Schema(query=Query)
    query = """
        query Reporter($id: ID!) {
          reporter(id: $id) {
            id
          }
        }
    """

    # Success.
    result = schema.execute(
        query, context=info_with_context().context, variables={"id": r1_id}
    )
    assert not result.errors
    assert result.data == {"reporter": {"id": r1_id}}

    # Filtered out.
    result = schema.execute(
        query, context=info_with_context().context, variables={"id": r2_id}
    )
    assert not result.errors
    assert result.data == {"reporter": None}
