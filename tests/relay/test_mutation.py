from rest_framework.permissions import IsAuthenticated

import graphene

from graphene import relay

from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.fields import DjangoField, DjangoListField
from graphene_djangorestframework.relay.mutation import DjangoClientIDMutation


from ..app.models import Reporter


def test_relay_django_mutation(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (relay.Node,)
            only_fields = ("id", "email")
            registry = Registry()

    class CreateReporter(DjangoClientIDMutation):
        class Input:
            email = graphene.String(required=True)

        reporter = graphene.Field(ReporterType)

        @classmethod
        def mutate_and_get_payload(cls, root, info, email):
            reporter = Reporter(id=1, email=email)
            return CreateReporter(reporter=reporter)

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)
    query = """
        mutation CreateReporter {
          createReporter (input: {email: "foo@bar.com"}) {
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
        "createReporter": {
            "reporter": {"id": "UmVwb3J0ZXJUeXBlOjE=", "email": "foo@bar.com"}
        }
    }


def test_relay_django_mutation_permissions_passed_to_field(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (relay.Node,)
            only_fields = ("id", "email")
            registry = Registry()

    class CreateReporter(DjangoClientIDMutation):
        class Input:
            email = graphene.String(required=True)

        reporter = graphene.Field(ReporterType)

        @classmethod
        def mutate_and_get_payload(cls, root, info, email):
            reporter = Reporter(id=1, email=email)
            return CreateReporter(reporter=reporter)

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field(permission_classes=[IsAuthenticated])

    schema = graphene.Schema(mutation=Mutation)
    query = """
        mutation CreateReporter {
          createReporter (input: {email: "foo@bar.com"}) {
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
