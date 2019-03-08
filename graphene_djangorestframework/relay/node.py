from functools import partial

from graphene.types.utils import get_type
from graphene.relay import node as graphene_node

from ..fields import check_permission_classes, check_throttle_classes


class DjangoNodeField(graphene_node.NodeField):
    def __init__(self, *args, **kwargs):
        self.permission_classes = kwargs.pop("permission_classes", None)
        self.throttle_classes = kwargs.pop("throttle_classes", None)

        super(DjangoNodeField, self).__init__(*args, **kwargs)

    def get_resolver(self, parent_resolver):
        return partial(
            self.node_type.node_resolver,
            get_type(self.field_type),
            self.permission_classes,
            self.throttle_classes,
        )


class DjangoNode(graphene_node.Node):
    @classmethod
    def Field(cls, *args, **kwargs):  # noqa: N802
        return DjangoNodeField(cls, *args, **kwargs)

    @classmethod
    def node_resolver(
        cls, only_type, permission_classes, throttle_classes, root, info, id
    ):
        check_permission_classes(info, cls, permission_classes)
        check_throttle_classes(info, cls, throttle_classes)

        return super(DjangoNode, cls).node_resolver(only_type, root, info, id)
