from django.conf.urls import url

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from graphene_djangorestframework.views import GraphQLAPIView
from graphene_djangorestframework.validators import (
    DocumentDepthValidator,
    DisableIntrospectionValidator,
)

from ..schema import schema
from ..middleware import TestMiddleware


class CustomGraphQLView(GraphQLAPIView):
    graphene_schema = schema
    graphiql = True
    graphene_pretty = True


class AuthenticatedGraphQLView(GraphQLAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)


class AuthenticatedAdminGraphQLView(GraphQLAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAdminUser,)


class CustomDepthValidator(DocumentDepthValidator):
    max_depth = 3


class DepthValidatedGraphQLView(GraphQLAPIView):
    graphene_validation_classes = [CustomDepthValidator]


class IntrospectionDisabledGraphQLView(GraphQLAPIView):
    graphene_validation_classes = [DisableIntrospectionValidator]


urlpatterns = [
    url(r"^graphql/inherited/$", CustomGraphQLView.as_view(graphiql=True)),
    url(
        r"^graphql/pretty/$",
        GraphQLAPIView.as_view(graphiql=True, graphene_pretty=True),
    ),
    url(r"^graphql/batch/$", GraphQLAPIView.as_view(graphene_batch=True)),
    url(r"^graphql/nographiql/$", GraphQLAPIView.as_view(graphiql=False)),
    url(
        r"^graphql/middleware-class/$",
        GraphQLAPIView.as_view(graphene_middleware=[TestMiddleware]),
    ),
    url(
        r"^graphql/middleware-instance/$",
        GraphQLAPIView.as_view(graphene_middleware=[TestMiddleware()]),
    ),
    url(r"^graphql/authenticated/$", AuthenticatedGraphQLView.as_view()),
    url(r"^graphql/authenticated-admin/$", AuthenticatedAdminGraphQLView.as_view()),
    url(r"^graphql/depth-limited/$", DepthValidatedGraphQLView.as_view()),
    url(
        r"^graphql/introspection-disabled/$", IntrospectionDisabledGraphQLView.as_view()
    ),
    url(r"^graphql/$", GraphQLAPIView.as_view(graphiql=True)),
]
