import pytest

from rest_framework import serializers

import graphene

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
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

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
}

type Mutation {
  updateReporter(input: UpdateReporterInput!): UpdateReporterPayload
  patchReporter(input: PatchReporterInput!): PatchReporterPayload
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
  firstName: String
  errors: [ErrorType]
  clientMutationId: String
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
  firstName: String
  errors: [ErrorType]
  clientMutationId: String
}
""".lstrip()
    )
