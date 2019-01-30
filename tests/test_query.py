import datetime

import pytest
from django.db import models
from django.utils.functional import SimpleLazyObject
from py.test import raises

from django.db.models import Q

import graphene
from graphene.relay import Node

from graphene_djangorestframework.compat import MissingType, JSONField
from graphene_djangorestframework.types import DjangoObjectType
from graphene_djangorestframework.settings import graphene_settings
from graphene_djangorestframework.registry import Registry

from .app.models import Article, CNNReporter, Reporter, Film, FilmDetails

pytestmark = pytest.mark.django_db


def test_should_query_only_fields():
    with pytest.raises(AssertionError) as e:

        class ReporterType(DjangoObjectType):
            class Meta:
                model = Reporter
                only_fields = ("articles",)
                registry = Registry()

        schema = graphene.Schema(query=ReporterType)
        query = """
            query ReporterQuery {
                articles
            }
        """
        result = schema.execute(query)

    assert e.value.args[0] == (
        "ReporterType fields must be a mapping (dict / OrderedDict) with "
        "field names as keys or a function which returns such a mapping."
    )


def test_should_query_simplelazy_objects():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            only_fields = ("id",)
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = graphene.Field(ReporterType)

        def resolve_reporter(self, info):
            return SimpleLazyObject(lambda: Reporter(id=1))

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporter {
            id
          }
        }
    """
    result = schema.execute(query)
    assert not result.errors
    assert result.data == {"reporter": {"id": "1"}}


def test_should_query_well():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            registry = Registry()

    class Query(graphene.ObjectType):
        reporter = graphene.Field(ReporterType)

        def resolve_reporter(self, info):
            return Reporter(first_name="ABA", last_name="X")

    query = """
        query ReporterQuery {
          reporter {
            firstName,
            lastName,
            email
          }
        }
    """
    expected = {"reporter": {"firstName": "ABA", "lastName": "X", "email": ""}}
    schema = graphene.Schema(query=Query)
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


@pytest.mark.skipif(JSONField is MissingType, reason="RangeField should exist")
def test_should_query_postgres_fields():
    from django.contrib.postgres.fields import (
        IntegerRangeField,
        ArrayField,
        JSONField,
        HStoreField,
    )

    class Event(models.Model):
        ages = IntegerRangeField(help_text="The age ranges")
        data = JSONField(help_text="Data")
        store = HStoreField()
        tags = ArrayField(models.CharField(max_length=50))

        class Meta:
            app_label = "tests"

    class EventType(DjangoObjectType):
        class Meta:
            model = Event
            registry = Registry()

    class Query(graphene.ObjectType):
        event = graphene.Field(EventType)

        def resolve_event(self, info):
            return Event(
                ages=(0, 10),
                data={"angry_babies": True},
                store={"h": "store"},
                tags=["child", "angry", "babies"],
            )

    schema = graphene.Schema(query=Query)
    query = """
        query myQuery {
          event {
            ages
            tags
            data
            store
          }
        }
    """
    expected = {
        "event": {
            "ages": [0, 10],
            "tags": ["child", "angry", "babies"],
            "data": '{"angry_babies": true}',
            "store": '{"h": "store"}',
        }
    }
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected

