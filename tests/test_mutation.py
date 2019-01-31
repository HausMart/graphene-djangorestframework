from django.utils.functional import SimpleLazyObject

from rest_framework.permissions import IsAuthenticated

import graphene

from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.mutation import DjangoMutation


from .app.models import Reporter


def test_django_mutation(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email")
            registry = Registry()

    class CreateReporter(DjangoMutation):
        class Arguments:
            email = graphene.String(required=True)

        reporter = graphene.Field(ReporterType)

        @classmethod
        def mutate(cls, root, info, email):
            reporter = SimpleLazyObject(lambda: Reporter(id=1, email=email))
            return CreateReporter(reporter=reporter)

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)
    query = """
        mutation CreateReporter {
          createReporter (email: "foo@bar.com") {
            reporter {
                id,
                email
            }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {
        "createReporter": {"reporter": {"id": "1", "email": "foo@bar.com"}}
    }


def test_django_mutation_permissions_passed_to_field(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email")
            registry = Registry()

    class CreateReporter(DjangoMutation):
        class Arguments:
            email = graphene.String(required=True)

        reporter = graphene.Field(ReporterType)

        @classmethod
        def mutate(cls, root, info, email):
            reporter = SimpleLazyObject(lambda: Reporter(id=1, email=email))
            return CreateReporter(reporter=reporter)

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field(permission_classes=[IsAuthenticated])

    schema = graphene.Schema(mutation=Mutation)
    query = """
        mutation CreateReporter {
          createReporter (email: "foo@bar.com") {
            reporter {
                id,
                email
            }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == "You do not have permission to perform this action."
    assert result.data == {"createReporter": None}
