import pytest

from django.utils.functional import SimpleLazyObject

from rest_framework import serializers

import graphene

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
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

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
  id: Int
  email: String
  firstName: String
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
""".lstrip()
    )


def test_serializer_client_id_mutation_create(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

        def create(self, validated_data):
            return SimpleLazyObject(lambda: Reporter(id=1, **validated_data))

    class CreateReporter(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation CreateReporter {
          createReporter (input: {email: "foo@bar.com", firstName: "Foo"}) {
            id,
            email,
            firstName
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {
        "createReporter": {"id": 1, "email": "foo@bar.com", "firstName": "Foo"}
    }
