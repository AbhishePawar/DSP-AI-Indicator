"""Knowledge Graph validation helpers — contracts only (I1.0).

No graph construction, traversal, querying, or persistence.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.exceptions import ValidationError

from knowledge_graph.enums import (
    EvidenceLinkCategory,
    LineageCategory,
    NodeCategory,
    RelationshipCategory,
)
from knowledge_graph.exceptions import KnowledgeGraphError

__all__ = [
    "NODE_CATEGORIES",
    "RELATIONSHIP_CATEGORIES",
    "EVIDENCE_LINK_CATEGORIES",
    "LINEAGE_CATEGORIES",
    "assert_evidence_link_category",
    "assert_lineage_category",
    "assert_node_category",
    "assert_relationship_category",
    "assert_unique_graph_ids",
    "require_decimal",
]

NODE_CATEGORIES: frozenset[NodeCategory] = frozenset(NodeCategory)
RELATIONSHIP_CATEGORIES: frozenset[RelationshipCategory] = frozenset(
    RelationshipCategory
)
EVIDENCE_LINK_CATEGORIES: frozenset[EvidenceLinkCategory] = frozenset(
    EvidenceLinkCategory
)
LINEAGE_CATEGORIES: frozenset[LineageCategory] = frozenset(LineageCategory)


def require_decimal(value: Any, *, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        msg = f"{field} must be decimal.Decimal, never float or other numeric types"
        raise ValidationError(msg)
    if not value.is_finite():
        msg = f"{field} must be a finite Decimal"
        raise ValidationError(msg)
    return value


def assert_node_category(category: NodeCategory) -> None:
    if category not in NODE_CATEGORIES:
        msg = f"illegal node categories: {category!r}"
        raise KnowledgeGraphError(msg)


def assert_relationship_category(category: RelationshipCategory) -> None:
    if category not in RELATIONSHIP_CATEGORIES:
        msg = f"illegal relationship categories: {category!r}"
        raise KnowledgeGraphError(msg)


def assert_evidence_link_category(category: EvidenceLinkCategory) -> None:
    if category not in EVIDENCE_LINK_CATEGORIES:
        msg = f"illegal evidence categories: {category!r}"
        raise KnowledgeGraphError(msg)


def assert_lineage_category(category: LineageCategory) -> None:
    if category not in LINEAGE_CATEGORIES:
        msg = f"illegal lineage categories: {category!r}"
        raise KnowledgeGraphError(msg)


def assert_unique_graph_ids(graph_ids: tuple[str, ...]) -> None:
    """Reject duplicate graph identities in a batch (assembler / registries)."""
    seen: set[str] = set()
    for raw in graph_ids:
        cleaned = raw.strip().lower()
        if not cleaned:
            msg = "graph_id must not be empty"
            raise ValidationError(msg)
        if cleaned in seen:
            msg = f"duplicate graph ids: {cleaned!r}"
            raise KnowledgeGraphError(msg)
        seen.add(cleaned)
