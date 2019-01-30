import mock

from django.core import management
from six import StringIO

import graphene_djangorestframework.settings

from graphene_djangorestframework.settings import (
    GrapheneSettings,
    IMPORT_STRINGS,
    DEFAULTS,
    graphene_settings,
)

from .schema import schema


@mock.patch(
    "graphene_djangorestframework.management.commands.graphql_schema.Command.save_file"
)
def test_generate_file_on_call_graphql_schema(savefile_mock):
    out = StringIO()
    management.call_command("graphql_schema", schema="", stdout=out)
    assert "Successfully dumped GraphQL schema to schema.json" in out.getvalue()


@mock.patch(
    "graphene_djangorestframework.management.commands.graphql_schema.Command.save_file"
)
def test_generate_file_on_call_graphql_schema_with_schema(savefile_mock):
    out = StringIO()
    management.call_command("graphql_schema", schema="tests.schema.schema", stdout=out)
    assert "Successfully dumped GraphQL schema to schema.json" in out.getvalue()


@mock.patch("json.dump")
def test_generate_file_on_call_graphql_schema_save_file(jsondump_mock):
    out = StringIO()
    management.call_command("graphql_schema", schema="", stdout=out)
    assert "Successfully dumped GraphQL schema to schema.json" in out.getvalue()

    jsondump_mock.assert_called_once_with(
        {"data": schema.introspect()}, mock.ANY, indent=None
    )


@mock.patch("json.dump")
def test_generate_file_on_call_graphql_schema_with_schema_save_file(
    jsondump_mock, settings
):
    out = StringIO()
    management.call_command("graphql_schema", schema=schema, stdout=out)
    assert "Successfully dumped GraphQL schema to schema.json" in out.getvalue()

    jsondump_mock.assert_called_once_with(
        {"data": schema.introspect()}, mock.ANY, indent=None
    )
