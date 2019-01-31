from django.utils.functional import SimpleLazyObject

from rest_framework.permissions import IsAuthenticated

import graphene

from graphene import relay

from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.types import DjangoObjectType
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
        reporters = DjangoConnectionField(ReporterType, permission_classes=[IsAuthenticated])

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