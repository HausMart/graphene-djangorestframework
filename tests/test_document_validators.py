import json

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


def url_string(string="/graphql/depth-limited/", **url_params):
    if url_params:
        string += "?" + urlencode(url_params)

    return string


def url_string_introspection(string="/graphql/introspection-disabled/", **url_params):
    if url_params:
        string += "?" + urlencode(url_params)

    return string


def test_document_depth_validation_with_three_nested_paths_allowed(api_client):
    response = api_client.get(
        url_string(
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        query helloNest { nest { test, nest { test nest { test } } } }
        """,
            operationName="helloNest",
        )
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "data": {
            "nest": {"nest": {"nest": {"test": "test"}, "test": "test"}, "test": "test"}
        }
    }


def test_document_depth_validation_with_four_nested_paths_not_allowed(api_client):
    response = api_client.get(
        url_string(
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        query helloNest { nest { test, nest { test nest { test nest { test } } } } }
        """,
            operationName="helloNest",
        )
    )

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {"message": 'Operation "helloNest" exceeds maximum operation depth of 3.'}
        ]
    }


def test_document_depth_validation_with_three_nested_paths_and_fragments_allowed(
    api_client
):
    response = api_client.get(
        url_string(
            query="""
        fragment shared on NestType {
          shared: nest {
              test
          }
        }
        query helloNest { nest { test, nest { test ...shared } } }
        """,
            operationName="helloNest",
        )
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "data": {
            "nest": {
                "nest": {"shared": {"test": "test"}, "test": "test"},
                "test": "test",
            }
        }
    }


def test_document_depth_validation_with_four_nested_paths_and_fragments_not_allowed(
    api_client
):
    response = api_client.get(
        url_string(
            query="""
        fragment shared on NestType {
          shared: nest {
              test
          }
        }
        query helloNest { nest { test, nest { test nest { ...shared } } } }
        """,
            operationName="helloNest",
        )
    )

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {"message": 'Operation "helloNest" exceeds maximum operation depth of 3.'}
        ]
    }


def test_document_schema_introspection_schema_not_allowed(api_client):
    response = api_client.get(
        url_string_introspection(
            query="""
{
  __schema {
    types {
      name
    }
  }
}"""
        )
    )

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {
                "message": "GraphQL introspection is not allowed, but the query contained __schema or __type."
            }
        ]
    }


def test_document_schema_introspection_type_not_allowed(api_client):
    response = api_client.get(
        url_string_introspection(
            query="""
{
  __type(name: "ReporterType") {
    name
  }
}"""
        )
    )

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {
                "message": "GraphQL introspection is not allowed, but the query contained __schema or __type."
            }
        ]
    }


def test_document_schema_introspection_everything_else_allowed(api_client):
    response = api_client.get(
        url_string_introspection(
            query="""
{
    test(who: "You")
}"""
        )
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello You"}}
