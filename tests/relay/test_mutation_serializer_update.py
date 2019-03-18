import pytest

from rest_framework import serializers

import graphene

from graphene import relay

from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.serializers import SerializerDjangoObjectTypeField
from graphene_djangorestframework.relay.mutation import SerializerClientIDUpdateMutation

from ..app.models import Reporter


def test_serializer_client_id_mutation_serializer_model_class_required():
    with pytest.raises(Exception) as e:

        class ReporterSerializer(serializers.Serializer):
            pass

        class CreateReporter(SerializerClientIDUpdateMutation):
            class Meta:
                serializer_class = ReporterSerializer

            @classmethod
            def mutate(cls, root, info, email):
                pass

    assert e.value.args[0] == "model_class is required for SerializerClientIDMutation"


def test_serializer_mutation_update_schema(info_with_context):
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
            fields = ("id", "email", "first_name", "reporter")
            read_only_fields = ("id",)
            extra_kwargs = {"first_name": {"write_only": True}}

    class UpdateReporter(SerializerClientIDUpdateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class PatchReporter(SerializerClientIDUpdateMutation):
        class Meta:
            serializer_class = ReporterSerializer
            partial = True

    class Mutation(graphene.ObjectType):
        update_reporter = UpdateReporter.Field()
        patch_reporter = PatchReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    assert (
        str(schema)
        == """
schema {
  mutation: Mutation
}

type ErrorType {
  field: String
  messages: [String!]!
  path: [String!]
}

type Mutation {
  updateReporter(input: UpdateReporterInput!): UpdateReporterPayload
  patchReporter(input: PatchReporterInput!): PatchReporterPayload
}

interface Node {
  id: ID!
}

input PatchReporterInput {
  email: String
  firstName: String
  id: ID!
  clientMutationId: String
}

type PatchReporterPayload {
  id: Int
  email: String
  reporter: ReporterType
  errors: [ErrorType]
  clientMutationId: String
}

type ReporterType implements Node {
  id: ID!
  firstName: String!
  email: String!
}

input UpdateReporterInput {
  email: String!
  firstName: String!
  id: ID!
  clientMutationId: String
}

type UpdateReporterPayload {
  id: Int
  email: String
  reporter: ReporterType
  errors: [ErrorType]
  clientMutationId: String
}
""".lstrip()
    )


update_doesnt_exist_registry = Registry()


def test_serializer_client_id_mutation_update_doesnt_exist(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email", "first_name")
            interfaces = (relay.Node,)
            registry = update_doesnt_exist_registry

        @classmethod
        def get_node(cls, info, id):
            assert id == "1"
            return None

    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("email", "first_name")

    class UpdateReporter(SerializerClientIDUpdateMutation):
        class Meta:
            serializer_class = ReporterSerializer
            registry = update_doesnt_exist_registry

    class Mutation(graphene.ObjectType):
        update_reporter = UpdateReporter.Field()

    schema = graphene.Schema(mutation=Mutation, types=[ReporterType])

    query = """
        mutation UpdateReporter {
          updateReporter (input: {id: "UmVwb3J0ZXJUeXBlOjE=", email: "foo@bar.com", firstName: "Foo"}) {
            email,
            firstName
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == "No Reporter matches the given query."
    assert result.data == {"updateReporter": None}


update_with_object_type_output_registry = Registry()


def test_serializer_client_id_mutation_update_with_object_type_output(
    info_with_context
):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email", "first_name")
            interfaces = (relay.Node,)
            registry = update_with_object_type_output_registry

        @classmethod
        def get_node(cls, info, id):
            assert id == "1"
            return Reporter(id=1, first_name="Foo", email="foo@bar.com")

    class ReporterSerializer(serializers.ModelSerializer):
        reporter = SerializerDjangoObjectTypeField(object_type=ReporterType)

        class Meta:
            model = Reporter
            fields = ("email", "first_name", "reporter")
            extra_kwargs = {
                "first_name": {"write_only": True},
                # "email": {"write_only": True},
            }

        def update(self, instance, validated_data):
            assert not self.partial
            assert validated_data == {"email": "foo2@bar.com", "first_name": "Foo2"}
            instance.email = validated_data.get("email")
            instance.first_name = validated_data.get("first_name")
            return instance

    class UpdateReporter(SerializerClientIDUpdateMutation):
        class Meta:
            serializer_class = ReporterSerializer
            registry = update_with_object_type_output_registry

    class Mutation(graphene.ObjectType):
        update_reporter = UpdateReporter.Field()

    schema = graphene.Schema(mutation=Mutation, types=[ReporterType])

    query = """
        mutation UpdateReporter {
          updateReporter (input: {id: "UmVwb3J0ZXJUeXBlOjE=", email: "foo2@bar.com", firstName: "Foo2"}) {
            reporter {
              id
              email
              firstName
            }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {
        "updateReporter": {
            "reporter": {
                "id": "UmVwb3J0ZXJUeXBlOjE=",
                "email": "foo2@bar.com",
                "firstName": "Foo2",
            }
        }
    }
