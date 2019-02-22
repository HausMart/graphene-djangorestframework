import json
import pytest

from rest_framework import serializers

import graphene

from graphene import relay

from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.serializers import (
    SerializerDjangoObjectTypeField,
    SerializerRelayIDField,
)
from graphene_djangorestframework.relay.mutation import SerializerClientIDCreateMutation

from ..app.models import Reporter, Article


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

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            only_fields = ("id", "headline", "pub_date")
            interfaces = (relay.Node,)
            registry = Registry()

    class ArticleSerializer(serializers.ModelSerializer):
        article = SerializerDjangoObjectTypeField(object_type=ArticleType)
        reporter = SerializerRelayIDField(object_type=ReporterType, write_only=True)

        class Meta:
            model = Article
            fields = ("headline", "pub_date", "article", "reporter")
            extra_kwargs = {"headline": {"write_only": True}}

    class CreateArticle(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ArticleSerializer

    class Mutation(graphene.ObjectType):
        create_article = CreateArticle.Field()

    schema = graphene.Schema(mutation=Mutation, types=[ReporterType])

    assert (
        str(schema)
        == """
schema {
  mutation: Mutation
}

type ArticleType implements Node {
  id: ID!
  headline: String!
  pubDate: Date!
}

input CreateArticleInput {
  headline: String!
  pubDate: Date!
  reporter: ID!
  clientMutationId: String
}

type CreateArticlePayload {
  pubDate: Date
  article: ArticleType
  errors: [ErrorType]
  clientMutationId: String
}

scalar Date

type ErrorType {
  field: String
  messages: [String!]!
}

type Mutation {
  createArticle(input: CreateArticleInput!): CreateArticlePayload
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
            fields = ("email", "first_name")

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
        "createReporter": {"email": "foo@bar.com", "firstName": "Foo"}
    }


def test_serializer_client_id_mutation_create_schema(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email", "first_name")
            interfaces = (relay.Node,)
            registry = Registry()

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            only_fields = ("id", "headline", "pub_date")
            interfaces = (relay.Node,)
            registry = Registry()

    class ArticleSerializer(serializers.ModelSerializer):
        article = SerializerDjangoObjectTypeField(object_type=ArticleType)
        reporter = SerializerRelayIDField(object_type=ReporterType, write_only=True)

        class Meta:
            model = Article
            fields = ("headline", "pub_date", "article", "reporter")
            extra_kwargs = {"headline": {"write_only": True}}

    class CreateArticle(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ArticleSerializer

    class Mutation(graphene.ObjectType):
        create_article = CreateArticle.Field()

    schema = graphene.Schema(mutation=Mutation, types=[ReporterType])

    assert (
        str(schema)
        == """
schema {
  mutation: Mutation
}

type ArticleType implements Node {
  id: ID!
  headline: String!
  pubDate: Date!
}

input CreateArticleInput {
  headline: String!
  pubDate: Date!
  reporter: ID!
  clientMutationId: String
}

type CreateArticlePayload {
  pubDate: Date
  article: ArticleType
  errors: [ErrorType]
  clientMutationId: String
}

scalar Date

type ErrorType {
  field: String
  messages: [String!]!
}

type Mutation {
  createArticle(input: CreateArticleInput!): CreateArticlePayload
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


def test_serializer_client_id_mutation_create_with_ID_input_validation(
    info_with_context
):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email", "first_name")
            interfaces = (relay.Node,)
            registry = Registry()

        @classmethod
        def get_node(cls, info, id):
            assert id == "1"
            return None

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            only_fields = ("id", "headline", "pub_date")
            interfaces = (relay.Node,)
            registry = Registry()

    class ArticleSerializer(serializers.ModelSerializer):
        article = SerializerDjangoObjectTypeField(object_type=ArticleType)
        reporter = SerializerRelayIDField(object_type=ReporterType, write_only=True)

        class Meta:
            model = Article
            fields = ("headline", "pub_date", "article", "reporter")
            extra_kwargs = {"headline": {"write_only": True}}

    class CreateArticle(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ArticleSerializer

    class Mutation(graphene.ObjectType):
        create_article = CreateArticle.Field()

    schema = graphene.Schema(mutation=Mutation, types=[ReporterType])

    # Test with invalid ID
    query = """
        mutation CreateArticle {
          createArticle (input: {headline: "Headline", reporter: "Foo", pubDate: "2019-01-01"}) {
              article {
                id
              }
              errors {
                  field
                  messages
              }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert json.loads(json.dumps(result.data)) == {
        "createArticle": {
            "errors": [{"field": "reporter", "messages": ["Not a valid ID."]}],
            "article": None,
        }
    }

    # Test with invalid ID (ReporterType:)
    query = """
        mutation CreateArticle {
          createArticle (input: {headline: "Headline", reporter: "UmVwb3J0ZXJUeXBlOg==", pubDate: "2019-01-01"}) {
              article {
                id
              }
              errors {
                  field
                  messages
              }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert json.loads(json.dumps(result.data)) == {
        "createArticle": {
            "errors": [{"field": "reporter", "messages": ["Not a valid ID."]}],
            "article": None,
        }
    }

    # Test with invalid ID (ArticleType:1)
    query = """
        mutation CreateArticle {
          createArticle (input: {headline: "Headline", reporter: "QXJ0aWNsZVR5cGU6MQ==", pubDate: "2019-01-01"}) {
              article {
                id
              }
              errors {
                  field
                  messages
              }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert json.loads(json.dumps(result.data)) == {
        "createArticle": {
            "errors": [
                {"field": "reporter", "messages": ["Must receive a ReporterType ID."]}
            ],
            "article": None,
        }
    }

    # Test with ID not found (ReporterType:1)
    query = """
        mutation CreateArticle {
          createArticle (input: {headline: "Headline", reporter: "UmVwb3J0ZXJUeXBlOjE=", pubDate: "2019-01-01"}) {
              article {
                id
              }
              errors {
                  field
                  messages
              }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert json.loads(json.dumps(result.data)) == {
        "createArticle": {
            "errors": [
                {
                    "field": "reporter",
                    "messages": ["No Reporter matches the given query."],
                }
            ],
            "article": None,
        }
    }


def test_serializer_client_id_mutation_create_with_ID_and_no_method_name(
    info_with_context
):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email", "first_name")
            interfaces = (relay.Node,)
            registry = Registry()

        @classmethod
        def get_node(cls, info, id):
            assert id == "1"
            return Reporter(id=1, first_name="Foo", email="foo@bar.com")

    class ArticleType(DjangoObjectType):
        reporter = graphene.Field(ReporterType)

        class Meta:
            model = Article
            only_fields = ("id", "headline", "pub_date")
            interfaces = (relay.Node,)
            registry = Registry()

    class ArticleSerializer(serializers.ModelSerializer):
        article = SerializerDjangoObjectTypeField(object_type=ArticleType)
        reporter = SerializerRelayIDField(object_type=ReporterType)

        def create(self, validated_data):
            return Article(id=1, **validated_data)

        class Meta:
            model = Article
            fields = ("headline", "pub_date", "article", "reporter")
            extra_kwargs = {"headline": {"write_only": True}}

    class CreateArticle(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ArticleSerializer

    class Mutation(graphene.ObjectType):
        create_article = CreateArticle.Field()

    schema = graphene.Schema(mutation=Mutation, types=[ReporterType])

    # Test with valid ID (ReporterType:1)
    query = """
        mutation CreateArticle {
          createArticle (input: {headline: "Headline", reporter: "UmVwb3J0ZXJUeXBlOjE=", pubDate: "2019-01-01"}) {
              article {
                id
                headline
                reporter {
                    id
                    firstName
                    email
                }
              }
              errors {
                  field
                  messages
              }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert json.loads(json.dumps(result.data)) == {
        "createArticle": {
            "errors": None,
            "article": {
                "id": "QXJ0aWNsZVR5cGU6MQ==",
                "headline": "Headline",
                "reporter": {
                    "id": "UmVwb3J0ZXJUeXBlOjE=",
                    "firstName": "Foo",
                    "email": "foo@bar.com",
                },
            },
        }
    }


def test_serializer_client_id_mutation_create_with_ID_and_method_name(
    info_with_context
):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id", "email", "first_name")
            interfaces = (relay.Node,)
            registry = Registry()

        @classmethod
        def get_node(cls, info, id):
            pytest.fail()

    class ArticleType(DjangoObjectType):
        reporter = graphene.Field(ReporterType)

        class Meta:
            model = Article
            only_fields = ("id", "headline", "pub_date")
            interfaces = (relay.Node,)
            registry = Registry()

    class ArticleSerializer(serializers.ModelSerializer):
        article = SerializerDjangoObjectTypeField(object_type=ArticleType)
        reporter = SerializerRelayIDField(
            object_type=ReporterType, method_name="resolve_reporter"
        )

        def resolve_reporter(self, value, object_type, object_id):
            assert value == "UmVwb3J0ZXJUeXBlOjE="
            assert object_type == ReporterType
            assert object_id == "1"
            return Reporter(
                id=1, first_name="FooResolved", email="foo-resolved@bar.com"
            )

        def create(self, validated_data):
            return Article(id=1, **validated_data)

        class Meta:
            model = Article
            fields = ("headline", "pub_date", "article", "reporter")
            extra_kwargs = {"headline": {"write_only": True}}

    class CreateArticle(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ArticleSerializer

    class Mutation(graphene.ObjectType):
        create_article = CreateArticle.Field()

    schema = graphene.Schema(mutation=Mutation, types=[ReporterType])

    # Test with valid ID (ReporterType:1)
    query = """
        mutation CreateArticle {
          createArticle (input: {headline: "Headline", reporter: "UmVwb3J0ZXJUeXBlOjE=", pubDate: "2019-01-01"}) {
              article {
                id
                headline
                reporter {
                    id
                    firstName
                    email
                }
              }
              errors {
                  field
                  messages
              }
          }
        }
    """
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert json.loads(json.dumps(result.data)) == {
        "createArticle": {
            "errors": None,
            "article": {
                "id": "QXJ0aWNsZVR5cGU6MQ==",
                "headline": "Headline",
                "reporter": {
                    "id": "UmVwb3J0ZXJUeXBlOjE=",
                    "firstName": "FooResolved",
                    "email": "foo-resolved@bar.com",
                },
            },
        }
    }
