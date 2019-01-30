import json
import pytest

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

j = lambda **kwargs: json.dumps(kwargs)
jl = lambda **kwargs: json.dumps([kwargs])


def url_string(string="/graphql/", **url_params):
    if url_params:
        string += "?" + urlencode(url_params)

    return string


def batch_url_string(**url_params):
    return url_string("/graphql/batch/", **url_params)


def test_graphiql_is_enabled(api_client):
    response = api_client.get(url_string(), HTTP_ACCEPT="text/html")
    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "text/html"


def test_graphiql_is_disabled(api_client):
    nographiql_url = "/graphql/nographiql/"
    response = api_client.get(url_string(nographiql_url), HTTP_ACCEPT="text/html")

    assert response.status_code == 400
    assert response["Content-Type"].split(";")[0] == "text/html"


def test_json_is_enabled(api_client):
    response = api_client.get(
        url_string(query="{test}"), HTTP_ACCEPT="application/json"
    )
    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "application/json"
    assert json.loads(response.content) == {"data": {"test": "Hello World"}}


def test_allows_get_with_query_param(api_client):
    response = api_client.get(url_string(query="{test}"))

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello World"}}


def test_allows_get_with_variable_values(api_client):
    response = api_client.get(
        url_string(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        )
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello Dolly"}}


def test_allows_get_with_operation_name(api_client):
    response = api_client.get(
        url_string(
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        """,
            operationName="helloWorld",
        )
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "data": {"test": "Hello World", "shared": "Hello Everyone"}
    }


def test_allows_get_with_null_operation_name(api_client):
    response = api_client.get(
        url_string(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
            operationName="null",
        )
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello Dolly"}}


def test_reports_validation_errors(api_client):
    response = api_client.get(url_string(query="{ test, unknownOne, unknownTwo }"))

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {
                "message": 'Cannot query field "unknownOne" on type "QueryRoot".',
                "locations": [{"line": 1, "column": 9}],
            },
            {
                "message": 'Cannot query field "unknownTwo" on type "QueryRoot".',
                "locations": [{"line": 1, "column": 21}],
            },
        ]
    }


def test_errors_when_missing_operation_name(api_client):
    response = api_client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """
        )
    )

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {
                "message": "Must provide operation name if query contains multiple operations."
            }
        ]
    }


def test_errors_when_sending_a_mutation_via_get(api_client):
    response = api_client.get(
        url_string(
            query="""
        mutation TestMutation { writeTest { test } }
        """
        )
    )
    assert response.status_code == 405
    assert json.loads(response.content) == {
        "errors": [
            {"message": "Can only perform a mutation operation from a POST request."}
        ]
    }


def test_sending_a_mutation_via_get_with_graphiql(api_client):
    response = api_client.get(
        url_string(
            query="""
        mutation TestMutation { writeTest { test } }
        """
        ),
        HTTP_ACCEPT="text/html",
    )

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "text/html"


def test_errors_when_selecting_a_mutation_within_a_get(api_client):
    response = api_client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """,
            operationName="TestMutation",
        )
    )

    assert response.status_code == 405
    assert json.loads(response.content) == {
        "errors": [
            {"message": "Can only perform a mutation operation from a POST request."}
        ]
    }


def test_allows_mutation_to_exist_within_a_get(api_client):
    response = api_client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """,
            operationName="TestQuery",
        )
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello World"}}


def test_allows_post_with_json_encoding(api_client):
    response = api_client.post(
        url_string(), j(query="{test}"), content_type="application/json"
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello World"}}


def test_batch_allows_post_with_json_encoding(api_client):
    response = api_client.post(
        batch_url_string(), jl(id=1, query="{test}"), content_type="application/json"
    )

    assert response.status_code == 200
    assert json.loads(response.content) == [
        {"id": 1, "data": {"test": "Hello World"}, "status": 200}
    ]


def test_batch_fails_if_is_empty(api_client):
    response = api_client.post(
        batch_url_string(), "[]", content_type="application/json"
    )

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {
                "message": "JSON parse error - Received an empty list in the batch request."
            }
        ]
    }


def test_allows_sending_a_mutation_via_post(api_client):
    response = api_client.post(
        url_string(),
        j(query="mutation TestMutation { writeTest { test } }"),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "data": {"writeTest": {"test": "Hello World"}}
    }


def test_allows_post_with_url_encoding(api_client):
    response = api_client.post(
        url_string(),
        urlencode(dict(query="{test}")),
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello World"}}


def test_supports_post_json_query_with_string_variables(api_client):
    response = api_client.post(
        url_string(),
        j(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello Dolly"}}


def test_batch_supports_post_json_query_with_string_variables(api_client):
    response = api_client.post(
        batch_url_string(),
        jl(
            id=1,
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == [
        {"id": 1, "data": {"test": "Hello Dolly"}, "status": 200}
    ]


def test_supports_post_json_query_with_json_variables(api_client):
    response = api_client.post(
        url_string(),
        j(
            query="query helloWho($who: String){ test(who: $who) }",
            variables={"who": "Dolly"},
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello Dolly"}}


def test_batch_supports_post_json_query_with_json_variables(api_client):
    response = api_client.post(
        batch_url_string(),
        jl(
            id=1,
            query="query helloWho($who: String){ test(who: $who) }",
            variables={"who": "Dolly"},
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == [
        {"id": 1, "data": {"test": "Hello Dolly"}, "status": 200}
    ]


def test_supports_post_url_encoded_query_with_string_variables(api_client):
    response = api_client.post(
        url_string(),
        urlencode(
            dict(
                query="query helloWho($who: String){ test(who: $who) }",
                variables=json.dumps({"who": "Dolly"}),
            )
        ),
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello Dolly"}}


def test_supports_post_json_quey_with_get_variable_values(api_client):
    response = api_client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        j(query="query helloWho($who: String){ test(who: $who) }"),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello Dolly"}}


def test_post_url_encoded_query_with_get_variable_values(api_client):
    response = api_client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        urlencode(dict(query="query helloWho($who: String){ test(who: $who) }")),
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello Dolly"}}


def test_supports_post_raw_text_query_with_get_variable_values(api_client):
    response = api_client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        "query helloWho($who: String){ test(who: $who) }",
        content_type="application/graphql",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello Dolly"}}


def test_allows_post_with_operation_name(api_client):
    response = api_client.post(
        url_string(),
        j(
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        """,
            operationName="helloWorld",
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "data": {"test": "Hello World", "shared": "Hello Everyone"}
    }


def test_batch_allows_post_with_operation_name(api_client):
    response = api_client.post(
        batch_url_string(),
        jl(
            id=1,
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        """,
            operationName="helloWorld",
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == [
        {
            "id": 1,
            "data": {"test": "Hello World", "shared": "Hello Everyone"},
            "status": 200,
        }
    ]


def test_allows_post_with_get_operation_name(api_client):
    response = api_client.post(
        url_string(operationName="helloWorld"),
        """
    query helloYou { test(who: "You"), ...shared }
    query helloWorld { test(who: "World"), ...shared }
    query helloDolly { test(who: "Dolly"), ...shared }
    fragment shared on QueryRoot {
      shared: test(who: "Everyone")
    }
    """,
        content_type="application/graphql",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "data": {"test": "Hello World", "shared": "Hello Everyone"}
    }


def test_inherited_class_with_attributes_works(api_client):
    inherited_url = "/graphql/inherited/"
    # Check schema and pretty attributes work
    response = api_client.post(url_string(inherited_url, query="{test}"))
    assert response.content.decode() == (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )

    # Check graphiql works
    response = api_client.get(url_string(inherited_url), HTTP_ACCEPT="text/html")
    assert response.status_code == 200


def test_supports_pretty_printing(api_client):
    pretty_url = "/graphql/pretty/"
    response = api_client.post(url_string(pretty_url, query="{test}"))

    assert response.content.decode() == (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )


def test_middleware_class_loaded(api_client):
    middleware_url = "/graphql/middleware-class/"
    response = api_client.post(url_string(middleware_url, query="{test}"))
    assert json.loads(response.content) == {"data": {"test": None}}


def test_middleware_instance_loaded(api_client):
    middleware_url = "/graphql/middleware-instance/"
    response = api_client.post(url_string(middleware_url, query="{test}"))
    assert json.loads(response.content) == {"data": {"test": None}}


def test_supports_pretty_printing_by_request(api_client):
    response = api_client.get(url_string(query="{test}", pretty="1"))

    assert response.content.decode() == (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )


def test_handles_field_errors_caught_by_graphql(api_client):
    response = api_client.get(url_string(query="{thrower}"))
    assert response.status_code == 200
    assert json.loads(response.content) == {
        "data": None,
        "errors": [
            {
                "locations": [{"column": 2, "line": 1}],
                "path": ["thrower"],
                "message": "Throws!",
            }
        ],
    }


def test_handles_syntax_errors_caught_by_graphql(api_client):
    response = api_client.get(url_string(query="syntaxerror"))
    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {
                "locations": [{"column": 1, "line": 1}],
                "message": "Syntax Error GraphQL (1:1) "
                'Unexpected Name "syntaxerror"\n\n1: syntaxerror\n   ^\n',
            }
        ]
    }


def test_handles_errors_caused_by_a_lack_of_query(api_client):
    response = api_client.get(url_string())

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [{"message": "Must provide query string."}]
    }


def test_handles_not_expected_json_bodies(api_client):
    response = api_client.post(url_string(), "[]", content_type="application/json")

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {
                "message": "JSON parse error - The received data is not a valid JSON query."
            }
        ]
    }


def test_handles_invalid_json_bodies(api_client):
    response = api_client.post(url_string(), "[oh}", content_type="application/json")

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {"message": "JSON parse error - Expecting value: line 1 column 2 (char 1)"}
        ]
    }


def test_handles_incomplete_json_bodies(api_client):
    response = api_client.post(
        url_string(), '{"query":', content_type="application/json"
    )

    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [
            {"message": "JSON parse error - Expecting value: line 1 column 10 (char 9)"}
        ]
    }


def test_handles_plain_post_text(api_client):
    response = api_client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        "query helloWho($who: String){ test(who: $who) }",
        content_type="text/plain",
    )

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello Dolly"}}


def test_handles_poorly_formed_variables(api_client):
    response = api_client.get(
        url_string(
            query="query helloWho($who: String){ test(who: $who) }", variables="who:You"
        )
    )
    assert response.status_code == 400
    assert json.loads(response.content) == {
        "errors": [{"message": "Variables are invalid JSON."}]
    }


def test_handles_unsupported_http_methods(api_client):
    response = api_client.put(url_string(query="{test}"))
    assert response.status_code == 405
    assert response["Allow"] == "GET, POST, HEAD, OPTIONS"
    assert json.loads(response.content) == {
        "errors": [{"message": 'Method "PUT" not allowed.'}]
    }


def test_passes_request_into_context_request(api_client):
    response = api_client.get(url_string(query="{request}", q="testing"))

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"request": "testing"}}


def test_djangorestframework_authentication_classes_unauthenticated(api_client):
    authenticated_url = "/graphql/authenticated/"
    response = api_client.post(url_string(authenticated_url, query="{test}"))

    assert response.status_code == 403
    assert json.loads(response.content) == {
        "errors": [{"message": "Authentication credentials were not provided."}]
    }


def test_djangorestframework_authentication_classes_authenticated(
    api_client, django_user_model
):
    authenticated_url = "/graphql/authenticated/"

    user = django_user_model.objects.create(username="user", password="password")

    api_client.force_authenticate(user)

    response = api_client.post(url_string(authenticated_url, query="{test}"))

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello World"}}

    user.delete()


def test_djangorestframework_permission_classes_unauthorized(
    api_client, django_user_model
):
    authenticated_url = "/graphql/authenticated-admin/"

    user = django_user_model.objects.create(username="user", password="password")

    api_client.force_authenticate(user)

    response = api_client.post(url_string(authenticated_url, query="{test}"))

    assert response.status_code == 403
    assert json.loads(response.content) == {
        "errors": [{"message": "You do not have permission to perform this action."}]
    }

    user.delete()


def test_djangorestframework_permission_classes_authorized(
    api_client, django_user_model
):
    authenticated_url = "/graphql/authenticated-admin/"

    user = django_user_model.objects.create_superuser(
        email="foo@bar.com", username="user", password="password"
    )

    api_client.force_authenticate(user)

    response = api_client.post(url_string(authenticated_url, query="{test}"))

    assert response.status_code == 200
    assert json.loads(response.content) == {"data": {"test": "Hello World"}}

    user.delete()
