import pytest

from rest_framework import serializers

import graphene

from graphene import relay

from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.serializers import SerializerDjangoObjectTypeField
from graphene_djangorestframework.relay.mutation import SerializerClientIDCreateMutation

from ..app.models import Reporter


def test_serializer_client_id_mutation_serializer_class_required():
    with pytest.raises(Exception) as e:

        class CreateReporter(SerializerClientIDCreateMutation):
            class Meta:
                pass

            @classmethod
            def mutate(cls, root, info, email):
                pass

    assert (
        e.value.args[0] == "serializer_class is required for SerializerClientIDMutation"
    )


def test_serializer_client_id_mutation_serializer_node_class_required():
    with pytest.raises(Exception) as e:

        class ReporterSerializer(serializers.ModelSerializer):
            class Meta:
                model = Reporter

        class CreateReporter(SerializerClientIDCreateMutation):
            class Meta:
                node_class = Exception
                serializer_class = ReporterSerializer

            @classmethod
            def mutate(cls, root, info, email):
                pass

    assert e.value.args[0] == "node_class must be a subclass of relay.Node"


def test_serializer_client_id_mutation_create_schema(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email", "first_name")
            interfaces = (relay.Node,)
            registry = Registry()

    class ReporterSerializer(serializers.ModelSerializer):
        reporter = SerializerDjangoObjectTypeField(object_type=ReporterType)

        class Meta:
            model = Reporter
            fields = ("email", "first_name", "reporter")
            extra_kwargs = {
                "first_name": {"write_only": True},
            }

    class CreateReporter(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    assert (
        str(schema)
        == """
schema {
  mutation: Mutation
}

input CreateReporterInput {
  email: String!
  firstName: String!
  clientMutationId: String
}

type CreateReporterPayload {
  email: String
  reporter: ReporterType
  errors: [ErrorType]
  clientMutationId: String
}

type ErrorType {
  field: String
  messages: [String!]!
}

type Mutation {
  createReporter(input: CreateReporterInput!): CreateReporterPayload
}

interface Node {
  id: ID!
}

type ReporterType implements Node {
  id: ID!
  firstName: String!
  email: String!
}
""".lstrip()
    )


def test_serializer_client_id_mutation_create_with_object_type_output(
    info_with_context
):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email", "first_name")
            interfaces = (relay.Node,)
            registry = Registry()

    class ReporterSerializer(serializers.ModelSerializer):
        reporter = SerializerDjangoObjectTypeField(object_type=ReporterType)

        class Meta:
            model = Reporter
            fields = ("email", "first_name", "reporter")
            extra_kwargs = {
                "first_name": {"write_only": True},
                "email": {"write_only": True},
            }

        def create(self, validated_data):
            return Reporter(id=1, **validated_data)

    class CreateReporter(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation CreateReporter {
          createReporter (input: {email: "foo@bar.com", firstName: "Foo"}) {
              reporter {
                id,
                email,
                firstName
              }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {
        "createReporter": {
            "reporter": {
                "id": "UmVwb3J0ZXJUeXBlOjE=",
                "email": "foo@bar.com",
                "firstName": "Foo",
            }
        }
    }


def test_serializer_client_id_mutation_create_with_serializer_output(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("email", "first_name",)

        def create(self, validated_data):
            return Reporter(id=1, **validated_data)

    class CreateReporter(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation CreateReporter {
          createReporter (input: {email: "foo@bar.com", firstName: "Foo"}) {
            email,
            firstName
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {
        "createReporter": {
            "email": "foo@bar.com",
            "firstName": "Foo",
        }
    }
