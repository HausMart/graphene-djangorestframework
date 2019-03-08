import re

from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError

from graphql.language.ast import (
    FragmentDefinition,
    OperationDefinition,
    Field,
    FragmentSpread,
    InlineFragment,
)


class BaseDocumentValidator:
    def allow_document(self, document, view):
        return True


class DocumentDepthValidator(BaseDocumentValidator):
    """
        Credit to https://github.com/stems/graphql-depth-limit.
    """

    default_message = _(
        'Operation "{operation}" exceeds maximum operation depth of {depth}.'
    )
    max_depth = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def allow_document(self, document, view):
        document_ast = document.document_ast
        definitions = document_ast.definitions

        fragments = self.get_fragments(definitions)
        queries = self.get_queries_and_mutations(definitions)

        for name in queries:
            try:
                self.determine_depth(queries[name], fragments, name)
            except ValidationError:
                return False

        return True

    def get_fragments(self, definitions):
        fragment_definitions = {
            d.name.value: d for d in definitions if isinstance(d, FragmentDefinition)
        }

        return fragment_definitions

    def get_queries_and_mutations(self, definitions):
        query_definitions = {
            d.name.value if d.name and d.name.value else "": d
            for d in definitions
            if isinstance(d, OperationDefinition)
        }

        return query_definitions

    def determine_depth(self, node, fragments, operation_name, current_depth=0):
        if current_depth > self.max_depth:
            self.message = force_text(self.default_message).format(
                operation=operation_name, depth=self.max_depth
            )
            raise ValidationError()

        if isinstance(node, Field):
            p = re.compile(r"^__")

            if p.match(node.name.value) or not node.selection_set:
                return 0

            return 1 + max(
                [
                    self.determine_depth(
                        selection, fragments, operation_name, current_depth + 1
                    )
                    for selection in node.selection_set.selections
                ]
            )
        elif isinstance(node, FragmentSpread):
            return self.determine_depth(
                fragments[node.name.value], fragments, operation_name, current_depth
            )
        elif (
            isinstance(node, InlineFragment)
            or isinstance(node, FragmentDefinition)
            or isinstance(node, OperationDefinition)
        ):
            return max(
                [
                    self.determine_depth(
                        selection, fragments, operation_name, current_depth
                    )
                    for selection in node.selection_set.selections
                ]
            )
        else:
            raise Exception("Depth validation failed. Couldn't parse node type.")
