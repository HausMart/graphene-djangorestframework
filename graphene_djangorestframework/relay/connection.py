from graphene import Field, Int
from graphene.relay import Connection


class DjangoConnection(Connection):
    """
    Since Django anyways always gets the total count of a queryset when
    paginating a response, this field can be safely added to a relay
    query response.
    """
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, node=None, name=None, **options):
        parent = super(DjangoConnection, cls).__init_subclass_with_meta__(
            node, name, **options
        )

        cls._meta.fields["total_count"] = Field(
            Int,
            name="totalCount",
            required=True,
            description="Total count for use in pagination",
        )

        return parent
