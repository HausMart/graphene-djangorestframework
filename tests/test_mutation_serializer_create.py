import pytest
import json

from django.utils.functional import SimpleLazyObject

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated

import graphene

from graphene_djangorestframework.mutation import SerializerCreateMutation

from .app.models import Reporter


def test_serializer_create_mutation_permissions_passed_to_field(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

        def create(self, validated_data):
            return SimpleLazyObject(lambda: Reporter(id=1, **validated_data))

    class CreateReporter(SerializerCreateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field(permission_classes=[IsAuthenticated])

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation CreateReporter {
          createReporter (email: "foo@bar.com", firstName: "Foo") {
            id,
            email,
            firstName
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == "You do not have permission to perform this action."
    assert result.data == {"createReporter": None}


def test_serializer_mutation_serializer_class_required():
    with pytest.raises(Exception) as e:

        class ReporterSerializer(serializers.Serializer):
            class Meta:
                model = Reporter

        class CreateReporter(SerializerCreateMutation):
            class Meta:
                pass

            @classmethod
            def mutate(cls, root, info, email):
                pass

    assert e.value.args[0] == "serializer_class is required for SerializerMutation"


def test_serializer_mutation_create_schema(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

    class CreateReporter(SerializerCreateMutation):
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

type CreateReporter {
  id: Int
  email: String
  firstName: String
  errors: [ErrorType]
}

type ErrorType {
  field: String
  messages: [String!]!
}

type Mutation {
  createReporter(email: String!, firstName: String!): CreateReporter
}
""".lstrip()
    )


def test_serializer_mutation_create(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

        def create(self, validated_data):
            return SimpleLazyObject(lambda: Reporter(id=1, **validated_data))

    class CreateReporter(SerializerCreateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation CreateReporter {
          createReporter (email: "foo@bar.com", firstName: "Foo") {
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


def test_serializer_mutation_create_validation(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

        def create(self, validated_data):
            return SimpleLazyObject(lambda: Reporter(id=1, **validated_data))

    class CreateReporter(SerializerCreateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation CreateReporter {
          createReporter (firstName: "") {
            id
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert len(result.errors) == 1
    assert (
        str(result.errors[0])
        == 'Field "createReporter" argument "email" of type "String!" is required but not provided.'
    )
    assert result.data is None

    query = """
        mutation CreateReporter {
          createReporter (firstName: "", email: "foobar") {
            id,
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
        "createReporter": {
            "id": None,
            "errors": [
                {"field": "email", "messages": ["Enter a valid email address."]},
                {"field": "firstName", "messages": ["This field may not be blank."]},
            ],
        }
    }


def test_serializer_mutation_create_serializer_validation(info_with_context):
    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("id", "email", "first_name")
            read_only_fields = ("id",)

        def create(self, validated_data):
            return SimpleLazyObject(lambda: Reporter(id=1, **validated_data))

    class CreateReporter(SerializerCreateMutation):
        class Meta:
            serializer_class = ReporterSerializer

    class Mutation(graphene.ObjectType):
        create_reporter = CreateReporter.Field()

    schema = graphene.Schema(mutation=Mutation)

    query = """
        mutation CreateReporter {
          createReporter (firstName: "") {
            id
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert len(result.errors) == 1
    assert (
        str(result.errors[0])
        == 'Field "createReporter" argument "email" of type "String!" is required but not provided.'
    )
    assert result.data is None

    query = """
        mutation CreateReporter {
          createReporter (firstName: "", email: "foobar") {
            id,
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
        "createReporter": {
            "id": None,
            "errors": [
                {"field": "email", "messages": ["Enter a valid email address."]},
                {"field": "firstName", "messages": ["This field may not be blank."]},
            ],
        }
    }
