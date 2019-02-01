import json

from rest_framework import serializers

import graphene

from graphene_djangorestframework.mutation import SerializerUpdateMutation

from .app.models import Reporter


def test_serializer_mutation_update_schema(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

    class UpdateReporter(SerializerUpdateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class PatchReporter(SerializerUpdateMutation):
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
  updateReporter(id: ID!, email: String!, firstName: String!): UpdateReporter
  patchReporter(id: ID!, email: String, firstName: String): PatchReporter
}

type PatchReporter {
  id: Int
  email: String
  firstName: String
  errors: [ErrorType]
}

type UpdateReporter {
  id: Int
  email: String
  firstName: String
  errors: [ErrorType]
}
""".lstrip()
    )


def test_serializer_mutation_update_partial(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

        def update(self, instance, validated_data):
            assert self.partial
            assert validated_data == {"email": "foo2@bar.com"}
            instance.email = validated_data.get("email")
            return instance

    class PatchReporter(SerializerUpdateMutation):
        class Meta:
            serializer_class = ReporterSerializer
            partial = True

        @classmethod
        def get_instance(cls, root, info, **input):
            lookup_field = cls._meta.lookup_field

            assert lookup_field == "id"
            assert input["id"] == "2"

            return Reporter(id=2, email="foo@bar.com")

    class Mutation(graphene.ObjectType):
        patch_reporter = PatchReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation PatchReporter {
          patchReporter (id: 2, email: "foo2@bar.com") {
            id
            email
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {"patchReporter": {"id": 2, "email": "foo2@bar.com"}}


def test_serializer_mutation_update_partial_validation(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

    class PatchReporter(SerializerUpdateMutation):
        class Meta:
            serializer_class = ReporterSerializer
            partial = True

        @classmethod
        def get_instance(cls, root, info, **input):
            return Reporter(id=2, email="foo@bar.com")

    class Mutation(graphene.ObjectType):
        patch_reporter = PatchReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation PatchReporter {
          patchReporter (id: 2, email: "") {
            id
            errors {
                field,
                messages
            }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert json.loads(json.dumps(result.data)) == {
        "patchReporter": {
            "id": None,
            "errors": [
                {"field": "email", "messages": ["This field may not be blank."]}
            ],
        }
    }


def test_serializer_mutation_update(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

        def update(self, instance, validated_data):
            assert not self.partial
            assert validated_data == {"email": "foo2@bar.com", "first_name": "foo2"}
            instance.email = validated_data.get("email")
            instance.first_name = validated_data.get("first_name")
            return instance

    class UpdateReporter(SerializerUpdateMutation):
        class Meta:
            serializer_class = ReporterSerializer

        @classmethod
        def get_instance(cls, root, info, **input):
            lookup_field = cls._meta.lookup_field

            assert lookup_field == "id"
            assert input["id"] == "2"

            return Reporter(id=2, email="foo@bar.com", first_name="foo")

    class Mutation(graphene.ObjectType):
        update_reporter = UpdateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation UpdateReporter {
          updateReporter (id: 2, email: "foo2@bar.com", firstName: "foo2") {
            id
            email
            firstName
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == {
        "updateReporter": {"id": 2, "email": "foo2@bar.com", "firstName": "foo2"}
    }


def test_serializer_mutation_update_validate(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

    class UpdateReporter(SerializerUpdateMutation):
        class Meta:
            serializer_class = ReporterSerializer

        @classmethod
        def get_instance(cls, root, info, **input):
            return Reporter(id=2, email="foo@bar.com", first_name="foo")

    class Mutation(graphene.ObjectType):
        update_reporter = UpdateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation UpdateReporter {
          updateReporter (id: 2, email: "foo2@bar.com") {
            id
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert len(result.errors) == 1
    assert (
        str(result.errors[0])
        == 'Field "updateReporter" argument "firstName" of type "String!" is required but not provided.'
    )
    assert not result.data
