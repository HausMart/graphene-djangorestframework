import pytest

import django_filters
from django_filters import OrderingFilter

from ..app.models import Article, Pet, Reporter


class ArticleFilter(django_filters.FilterSet):
    class Meta:
        model = Article
        fields = {
            "headline": ["exact", "icontains"],
            "pub_date": ["gt", "lt", "exact"],
            "reporter": ["exact"],
        }

    order_by = OrderingFilter(fields=("pub_date",))


class ReporterFilter(django_filters.FilterSet):
    class Meta:
        model = Reporter
        fields = ["first_name", "last_name", "email", "pets"]

    order_by = OrderingFilter(fields=("pub_date",))


class PetFilter(django_filters.FilterSet):
    class Meta:
        model = Pet
        fields = ["name"]


@pytest.fixture()
def article_filter():
    return ArticleFilter


@pytest.fixture()
def reporter_filter():
    return ReporterFilter


@pytest.fixture()
def pet_filter():
    return PetFilter
