from datetime import datetime

import pytest
import pytz

from graphene import Field, ObjectType, Schema, Argument, Float, Boolean, String
from graphene.relay import Node
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.filter.forms import (
    GlobalIDFormField,
    GlobalIDMultipleChoiceField,
)
from graphene_djangorestframework.registry import Registry
from graphene_djangorestframework.utils import DJANGO_FILTER_INSTALLED

# for annotation test
from django.db.models import TextField, Value
from django.db.models.functions import Concat

from ..app.models import Article, Pet, Reporter

pytestmark = []

if DJANGO_FILTER_INSTALLED:
    import django_filters
    from django_filters import FilterSet, NumberFilter

    from graphene_djangorestframework.filter import (
        GlobalIDFilter,
        DjangoFilterConnectionField,
        GlobalIDMultipleChoiceFilter,
    )

    # from graphene_django.filter.tests.filters import (
    #     ArticleFilter,
    #     PetFilter,
    #     ReporterFilter,
    # )
else:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )

pytestmark.append(pytest.mark.django_db)


if DJANGO_FILTER_INSTALLED:
    filter_registry = Registry()

    class ArticleNode(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            filter_fields = ("headline",)
            registry = filter_registry

    class ReporterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            registry = filter_registry

    class PetNode(DjangoObjectType):
        class Meta:
            model = Pet
            interfaces = (Node,)
            registry = filter_registry

    # schema = Schema()


def get_args(field):
    return field.args


def assert_arguments(field, *arguments):
    ignore = ("after", "before", "first", "last", "order_by")
    args = get_args(field)
    actual = [name for name in args if name not in ignore and not name.startswith("_")]
    assert set(arguments) == set(
        actual
    ), "Expected arguments ({}) did not match actual ({})".format(arguments, actual)


def assert_orderable(field):
    args = get_args(field)
    assert "order_by" in args, "Field cannot be ordered"


def assert_not_orderable(field):
    args = get_args(field)
    assert "order_by" not in args, "Field can be ordered"


def test_filter_explicit_filterset_arguments(article_filter):
    field = DjangoFilterConnectionField(ArticleNode, filterset_class=article_filter)
    assert_arguments(
        field,
        "headline",
        "headline__icontains",
        "pub_date",
        "pub_date__gt",
        "pub_date__lt",
        "reporter",
    )


def test_filter_shortcut_filterset_arguments_list():
    field = DjangoFilterConnectionField(ArticleNode, fields=["pub_date", "reporter"])
    assert_arguments(field, "pub_date", "reporter")


def test_filter_shortcut_filterset_arguments_dict():
    field = DjangoFilterConnectionField(
        ArticleNode, fields={"headline": ["exact", "icontains"], "reporter": ["exact"]}
    )
    assert_arguments(field, "headline", "headline__icontains", "reporter")


def test_filter_explicit_filterset_orderable(reporter_filter):
    field = DjangoFilterConnectionField(ReporterNode, filterset_class=reporter_filter)
    assert_orderable(field)


# def test_filter_shortcut_filterset_orderable_true():
#     field = DjangoFilterConnectionField(ReporterNode)
#     assert_not_orderable(field)


# def test_filter_shortcut_filterset_orderable_headline():
#     field = DjangoFilterConnectionField(ReporterNode, order_by=['headline'])
#     assert_orderable(field)


def test_filter_explicit_filterset_not_orderable(pet_filter):
    field = DjangoFilterConnectionField(PetNode, filterset_class=pet_filter)
    assert_not_orderable(field)


def test_filter_shortcut_filterset_extra_meta():
    field = DjangoFilterConnectionField(
        ArticleNode, extra_filter_meta={"exclude": ("headline",)}
    )
    assert "headline" not in field.filterset_class.get_fields()


def test_filter_shortcut_filterset_context(info_with_context):
    class ArticleContextFilter(django_filters.FilterSet):
        class Meta:
            model = Article
            exclude = set()

        @property
        def qs(self):
            qs = super(ArticleContextFilter, self).qs
            return qs.filter(reporter=self.request.reporter)

    class Query(ObjectType):
        context_articles = DjangoFilterConnectionField(
            ArticleNode, filterset_class=ArticleContextFilter
        )

    r1 = Reporter.objects.create(first_name="r1", last_name="r1", email="r1@test.com")
    r2 = Reporter.objects.create(first_name="r2", last_name="r2", email="r2@test.com")
    Article.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(tz=pytz.UTC),
        reporter=r1,
        editor=r1,
    )
    Article.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(tz=pytz.UTC),
        reporter=r2,
        editor=r2,
    )

    query = """
    query {
        contextArticles {
            edges {
                node {
                    headline
                }
            }
        }
    }
    """
    schema = Schema(query=Query)
    context = info_with_context().context
    context.get("request").reporter = r2
    result = schema.execute(query, context=context)
    assert not result.errors

    assert len(result.data["contextArticles"]["edges"]) == 1
    assert result.data["contextArticles"]["edges"][0]["node"]["headline"] == "a2"


def test_filter_filterset_information_on_meta():
    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            filter_fields = ["first_name", "articles"]
            registry = filter_registry

    field = DjangoFilterConnectionField(ReporterFilterNode)
    assert_arguments(field, "first_name", "articles")
    assert_not_orderable(field)


def test_filter_filterset_information_on_meta_related():
    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            filter_fields = ["first_name", "articles"]
            registry = filter_registry

    class ArticleFilterNode(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            filter_fields = ["headline", "reporter"]
            registry = filter_registry

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterFilterNode)
        all_articles = DjangoFilterConnectionField(ArticleFilterNode)
        reporter = Field(ReporterFilterNode)
        article = Field(ArticleFilterNode)

    schema = Schema(query=Query)
    articles_field = ReporterFilterNode._meta.fields["articles"].get_type()
    assert_arguments(articles_field, "headline", "reporter")
    assert_not_orderable(articles_field)


def test_filter_filterset_related_results():
    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            filter_fields = ["first_name", "articles"]
            registry = filter_registry

    class ArticleFilterNode(DjangoObjectType):
        class Meta:
            interfaces = (Node,)
            model = Article
            filter_fields = ["headline", "reporter"]
            registry = filter_registry

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterFilterNode)
        all_articles = DjangoFilterConnectionField(ArticleFilterNode)
        reporter = Field(ReporterFilterNode)
        article = Field(ArticleFilterNode)

    r1 = Reporter.objects.create(first_name="r1", last_name="r1", email="r1@test.com")
    r2 = Reporter.objects.create(first_name="r2", last_name="r2", email="r2@test.com")
    Article.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(tz=pytz.UTC),
        reporter=r1,
    )
    Article.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(tz=pytz.UTC),
        reporter=r2,
    )

    query = """
    query {
        allReporters {
            edges {
                node {
                    articles {
                        edges {
                            node {
                                headline
                            }
                        }
                    }
                }
            }
        }
    }
    """
    schema = Schema(query=Query)
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    # We should only get back a single article for each reporter
    assert (
        len(result.data["allReporters"]["edges"][0]["node"]["articles"]["edges"]) == 1
    )
    assert (
        len(result.data["allReporters"]["edges"][1]["node"]["articles"]["edges"]) == 1
    )


def test_global_id_field_implicit():
    field = DjangoFilterConnectionField(ArticleNode, fields=["id"])
    filterset_class = field.filterset_class
    id_filter = filterset_class.base_filters["id"]
    assert isinstance(id_filter, GlobalIDFilter)
    assert id_filter.field_class == GlobalIDFormField


def test_global_id_field_explicit():
    class ArticleIdFilter(django_filters.FilterSet):
        class Meta:
            model = Article
            fields = ["id"]

    field = DjangoFilterConnectionField(ArticleNode, filterset_class=ArticleIdFilter)
    filterset_class = field.filterset_class
    id_filter = filterset_class.base_filters["id"]
    assert isinstance(id_filter, GlobalIDFilter)
    assert id_filter.field_class == GlobalIDFormField


def test_filterset_descriptions():
    class ArticleIdFilter(django_filters.FilterSet):
        class Meta:
            model = Article
            fields = ["id"]

        max_time = django_filters.NumberFilter(
            method="filter_max_time", label="The maximum time"
        )

    field = DjangoFilterConnectionField(ArticleNode, filterset_class=ArticleIdFilter)
    max_time = field.args["max_time"]
    assert isinstance(max_time, Argument)
    assert max_time.type == Float
    assert max_time.description == "The maximum time"


def test_global_id_field_relation():
    field = DjangoFilterConnectionField(ArticleNode, fields=["reporter"])
    filterset_class = field.filterset_class
    id_filter = filterset_class.base_filters["reporter"]
    assert isinstance(id_filter, GlobalIDFilter)
    assert id_filter.field_class == GlobalIDFormField


def test_global_id_multiple_field_implicit():
    field = DjangoFilterConnectionField(ReporterNode, fields=["pets"])
    filterset_class = field.filterset_class
    multiple_filter = filterset_class.base_filters["pets"]
    assert isinstance(multiple_filter, GlobalIDMultipleChoiceFilter)
    assert multiple_filter.field_class == GlobalIDMultipleChoiceField


def test_global_id_multiple_field_explicit():
    class ReporterPetsFilter(django_filters.FilterSet):
        class Meta:
            model = Reporter
            fields = ["pets"]

    field = DjangoFilterConnectionField(
        ReporterNode, filterset_class=ReporterPetsFilter
    )
    filterset_class = field.filterset_class
    multiple_filter = filterset_class.base_filters["pets"]
    assert isinstance(multiple_filter, GlobalIDMultipleChoiceFilter)
    assert multiple_filter.field_class == GlobalIDMultipleChoiceField


def test_global_id_multiple_field_implicit_reverse():
    field = DjangoFilterConnectionField(ReporterNode, fields=["articles"])
    filterset_class = field.filterset_class
    multiple_filter = filterset_class.base_filters["articles"]
    assert isinstance(multiple_filter, GlobalIDMultipleChoiceFilter)
    assert multiple_filter.field_class == GlobalIDMultipleChoiceField


def test_global_id_multiple_field_explicit_reverse():
    class ReporterPetsFilter(django_filters.FilterSet):
        class Meta:
            model = Reporter
            fields = ["articles"]

    field = DjangoFilterConnectionField(
        ReporterNode, filterset_class=ReporterPetsFilter
    )
    filterset_class = field.filterset_class
    multiple_filter = filterset_class.base_filters["articles"]
    assert isinstance(multiple_filter, GlobalIDMultipleChoiceFilter)
    assert multiple_filter.field_class == GlobalIDMultipleChoiceField


def test_filter_filterset_related_results(info_with_context):
    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            filter_fields = {"first_name": ["icontains"]}
            registry = filter_registry

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterFilterNode)

    r1 = Reporter.objects.create(
        first_name="A test user", last_name="Last Name", email="test1@test.com"
    )
    r2 = Reporter.objects.create(
        first_name="Other test user",
        last_name="Other Last Name",
        email="test2@test.com",
    )
    r3 = Reporter.objects.create(
        first_name="Random", last_name="RandomLast", email="random@test.com"
    )

    query = """
    query {
        allReporters(firstName_Icontains: "test") {
            edges {
                node {
                    id
                }
            }
        }
    }
    """
    schema = Schema(query=Query)
    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    # We should only get two reporters
    assert len(result.data["allReporters"]["edges"]) == 2


def test_recursive_filter_connection():
    class ReporterFilterNode(DjangoObjectType):
        child_reporters = DjangoFilterConnectionField(lambda: ReporterFilterNode)

        def resolve_child_reporters(self, **args):
            return []

        class Meta:
            model = Reporter
            interfaces = (Node,)
            registry = filter_registry

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterFilterNode)

    assert (
        ReporterFilterNode._meta.fields["child_reporters"].node_type
        == ReporterFilterNode
    )


def test_should_query_filter_node_limit(info_with_context):
    class ReporterFilter(FilterSet):
        limit = NumberFilter(method="filter_limit")

        def filter_limit(self, queryset, name, value):
            return queryset[:value]

        class Meta:
            model = Reporter
            fields = ["first_name"]

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            registry = filter_registry

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            filter_fields = ("lang",)
            registry = filter_registry

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(
            ReporterType, filterset_class=ReporterFilter
        )

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.order_by("a_choice")

    Reporter.objects.create(
        first_name="Bob", last_name="Doe", email="bobdoe@example.com", a_choice=2
    )
    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    Article.objects.create(
        headline="Article Node 1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(tz=pytz.UTC),
        reporter=r,
        editor=r,
        lang="es",
    )
    Article.objects.create(
        headline="Article Node 2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(tz=pytz.UTC),
        reporter=r,
        editor=r,
        lang="en",
    )

    schema = Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters(limit: 1) {
                edges {
                    node {
                        id
                        firstName
                        articles(lang: "es") {
                            edges {
                                node {
                                    id
                                    lang
                                }
                            }
                        }
                    }
                }
            }
        }
    """

    expected = {
        "allReporters": {
            "edges": [
                {
                    "node": {
                        "id": "UmVwb3J0ZXJUeXBlOjI=",
                        "firstName": "John",
                        "articles": {
                            "edges": [
                                {"node": {"id": "QXJ0aWNsZVR5cGU6MQ==", "lang": "ES"}}
                            ]
                        },
                    }
                }
            ]
        }
    }

    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == expected


def test_should_query_filter_node_double_limit_raises(info_with_context):
    class ReporterFilter(FilterSet):
        limit = NumberFilter(method="filter_limit")

        def filter_limit(self, queryset, name, value):
            return queryset[:value]

        class Meta:
            model = Reporter
            fields = ["first_name"]

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            registry = filter_registry

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(
            ReporterType, filterset_class=ReporterFilter
        )

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.order_by("a_choice")[:2]

    Reporter.objects.create(
        first_name="Bob", last_name="Doe", email="bobdoe@example.com", a_choice=2
    )
    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    schema = Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters(limit: 1) {
                edges {
                    node {
                        id
                        firstName
                    }
                }
            }
        }
    """

    result = schema.execute(query, context=info_with_context().context)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == (
        "Received two sliced querysets (high mark) in the connection, please slice only in one."
    )


def test_order_by_is_perserved(info_with_context):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            filter_fields = ()
            registry = filter_registry

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(
            ReporterType, reverse_order=Boolean()
        )

        def resolve_all_reporters(self, info, reverse_order=False, **args):
            reporters = Reporter.objects.order_by("first_name")

            if reverse_order:
                return reporters.reverse()

            return reporters

    Reporter.objects.create(first_name="b")
    r = Reporter.objects.create(first_name="a")

    schema = Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters(first: 1) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    expected = {"allReporters": {"edges": [{"node": {"firstName": "a"}}]}}

    result = schema.execute(query, context=info_with_context().context)
    assert not result.errors
    assert result.data == expected

    reverse_query = """
        query NodeFilteringQuery {
            allReporters(first: 1, reverseOrder: true) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    reverse_expected = {"allReporters": {"edges": [{"node": {"firstName": "b"}}]}}

    reverse_result = schema.execute(reverse_query, context=info_with_context().context)

    assert not reverse_result.errors
    assert reverse_result.data == reverse_expected


def test_annotation_is_perserved(info_with_context):
    class ReporterType(DjangoObjectType):
        full_name = String()

        def resolve_full_name(instance, info, **args):
            return instance.full_name

        class Meta:
            model = Reporter
            interfaces = (Node,)
            filter_fields = ()
            registry = filter_registry

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterType)

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.annotate(
                full_name=Concat(
                    "first_name", Value(" "), "last_name", output_field=TextField()
                )
            )

    Reporter.objects.create(first_name="John", last_name="Doe")

    schema = Schema(query=Query)

    query = """
        query NodeFilteringQuery {
            allReporters(first: 1) {
                edges {
                    node {
                        fullName
                    }
                }
            }
        }
    """
    expected = {"allReporters": {"edges": [{"node": {"fullName": "John Doe"}}]}}

    result = schema.execute(query, context=info_with_context().context)

    assert not result.errors
    assert result.data == expected


def test_get_queryset_is_used(info_with_context):
    class ReporterType(DjangoObjectType):
        @classmethod
        def get_queryset(cls, info):
            return Reporter.objects.none()

        class Meta:
            model = Reporter
            interfaces = (Node,)
            filter_fields = ()
            registry = filter_registry

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterType)

    Reporter.objects.create(first_name="John", last_name="Doe")

    schema = Schema(query=Query)

    query = """
        query NodeFilteringQuery {
            allReporters {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    expected = {"allReporters": {"edges": []}}

    result = schema.execute(query, context=info_with_context().context)

    assert not result.errors
    assert result.data == expected
