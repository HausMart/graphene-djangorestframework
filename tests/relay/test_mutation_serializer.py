import pytest

from rest_framework import serializers

import graphene

from graphene import relay

from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.serializers import SerializerDjangoObjectTypeField
from graphene_djangorestframework.relay.mutation import (
    SerializerClientIDCreateMutation,
    SerializerClientIDUpdateMutation,
)

from ..app.models import Reporter, Article

_schema_with_same_serializer_input_registry = Registry()


def test_serializer_mutation_schema_with_same_serializer_input(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            interfaces = (relay.Node,)
            registry = _schema_with_same_serializer_input_registry

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            only_fields = ("id",)
            interfaces = (relay.Node,)
            registry = _schema_with_same_serializer_input_registry

    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = ("email", "first_name")

    class ArticleSerializer(serializers.ModelSerializer):
        reporter = ReporterSerializer(write_only=True)

        class Meta:
            model = Article
            fields = ("reporter",)

    class CreateArticle(SerializerClientIDCreateMutation):
        class Meta:
            serializer_class = ArticleSerializer

    class UpdateArticle(SerializerClientIDUpdateMutation):
        class Meta:
            serializer_class = ArticleSerializer

    class Mutation(graphene.ObjectType):
        create_article = CreateArticle.Field()
        update_article = UpdateArticle.Field()

    schema = graphene.Schema(mutation=Mutation)

    assert (
        str(schema)
        == """
schema {
  mutation: Mutation
}

input CreateArticleInput {
  reporter: ReporterSerializerInput!
  clientMutationId: String
}

type CreateArticlePayload {
  errors: [ErrorType]
  clientMutationId: String
}

type ErrorType {
  field: String
  messages: [String!]!
  path: [String!]
}

type Mutation {
  createArticle(input: CreateArticleInput!): CreateArticlePayload
  updateArticle(input: UpdateArticleInput!): UpdateArticlePayload
}

input ReporterSerializerInput {
  email: String!
  firstName: String!
}

input UpdateArticleInput {
  reporter: ReporterSerializerInput!
  id: ID!
  clientMutationId: String
}

type UpdateArticlePayload {
  errors: [ErrorType]
  clientMutationId: String
}
""".lstrip()
    )
