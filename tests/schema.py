import graphene
from graphene import ObjectType, Schema

from graphene_djangorestframework.types import DjangoObjectType

from .app.models import Reporter


class ReporterType(DjangoObjectType):
    class Meta:
        model = Reporter


class QueryRoot(ObjectType):
    thrower = graphene.String(required=True)
    request = graphene.String(required=True)
    test = graphene.String(who=graphene.String())

    def resolve_thrower(self, info):
        raise Exception("Throws!")

    def resolve_request(self, info):
        return info.context.get("request").GET.get("q")

    def resolve_test(self, info, who=None):
        return "Hello %s" % (who or "World")


class MutationRoot(ObjectType):
    write_test = graphene.Field(QueryRoot)

    def resolve_write_test(self, info):
        return QueryRoot()


schema = Schema(query=QueryRoot, mutation=MutationRoot)