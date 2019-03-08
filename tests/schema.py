import graphene
from graphene import ObjectType, Schema

from graphene_djangorestframework.types import DjangoObjectType

from .app.models import Reporter


class ReporterType(DjangoObjectType):
    class Meta:
        model = Reporter


class NestType(ObjectType):
    test = graphene.String()
    nest = graphene.Field("tests.schema.NestType")

    def resolve_test(self, info):
        return "test"

    def resolve_nest(self, info):
        return {}


class QueryRoot(ObjectType):
    thrower = graphene.String(required=True)
    request = graphene.String(required=True)
    test = graphene.String(who=graphene.String())
    nest = graphene.Field(NestType)

    def resolve_thrower(self, info):
        raise Exception("Throws!")

    def resolve_request(self, info):
        return info.context.get("request").GET.get("q")

    def resolve_test(self, info, who=None):
        return "Hello %s" % (who or "World")

    def resolve_nest(self, info):
        return {}


class MutationRoot(ObjectType):
    write_test = graphene.Field(QueryRoot)

    def resolve_write_test(self, info):
        return QueryRoot()


schema = Schema(query=QueryRoot, mutation=MutationRoot)
