"""Industry taxonomy — identity store and hierarchy traversal."""

from __future__ import annotations

from industry.enums import IdentityLifecycle
from industry.exceptions import IndustryError
from industry.models import IndustryIdentity

__all__ = ["IndustryTaxonomy"]


class IndustryTaxonomy:
    """Lightweight hierarchy of DSP IndustryIdentity nodes.

    No valuation, methodology, or peer logic — identity structure only.
    """

    def __init__(self) -> None:
        self._identities: dict[str, IndustryIdentity] = {}

    def register(self, identity: IndustryIdentity) -> IndustryIdentity:
        """Register an identity. Rejects duplicate ids."""
        if identity.id in self._identities:
            msg = f"duplicate industry identity: {identity.id!r}"
            raise IndustryError(msg)
        if identity.parent_id is not None and identity.parent_id not in self._identities:
            msg = (
                f"unknown parent_id {identity.parent_id!r} for identity "
                f"{identity.id!r}"
            )
            raise IndustryError(msg)
        if identity.parent_id is not None:
            self._assert_no_cycle(identity.id, identity.parent_id)
        self._identities[identity.id] = identity
        return identity

    def get(self, industry_id: str) -> IndustryIdentity:
        key = industry_id.strip().lower()
        try:
            return self._identities[key]
        except KeyError as exc:
            msg = f"unknown industry identity: {key!r}"
            raise IndustryError(msg) from exc

    def contains(self, industry_id: str) -> bool:
        return industry_id.strip().lower() in self._identities

    def __len__(self) -> int:
        return len(self._identities)

    def list_identities(
        self,
        *,
        status: IdentityLifecycle | None = None,
    ) -> tuple[IndustryIdentity, ...]:
        items = list(self._identities.values())
        if status is not None:
            items = [i for i in items if i.status is status]
        return tuple(sorted(items, key=lambda i: i.id))

    def children(self, industry_id: str) -> tuple[IndustryIdentity, ...]:
        parent = self.get(industry_id)
        kids = [
            i for i in self._identities.values() if i.parent_id == parent.id
        ]
        return tuple(sorted(kids, key=lambda i: i.id))

    def parent(self, industry_id: str) -> IndustryIdentity | None:
        identity = self.get(industry_id)
        if identity.parent_id is None:
            return None
        return self.get(identity.parent_id)

    def ancestors(self, industry_id: str) -> tuple[IndustryIdentity, ...]:
        """Return ancestors from immediate parent up to root."""
        chain: list[IndustryIdentity] = []
        current = self.get(industry_id)
        seen: set[str] = {current.id}
        while current.parent_id is not None:
            if current.parent_id in seen:
                msg = f"circular hierarchy detected at {current.parent_id!r}"
                raise IndustryError(msg)
            current = self.get(current.parent_id)
            seen.add(current.id)
            chain.append(current)
        return tuple(chain)

    def descendants(self, industry_id: str) -> tuple[IndustryIdentity, ...]:
        """Return all descendants in deterministic id order (BFS)."""
        root = self.get(industry_id)
        found: list[IndustryIdentity] = []
        queue = list(self.children(root.id))
        seen = {root.id}
        while queue:
            node = queue.pop(0)
            if node.id in seen:
                msg = f"circular hierarchy detected at {node.id!r}"
                raise IndustryError(msg)
            seen.add(node.id)
            found.append(node)
            queue.extend(self.children(node.id))
        return tuple(sorted(found, key=lambda i: i.id))

    def roots(self) -> tuple[IndustryIdentity, ...]:
        return tuple(
            sorted(
                (i for i in self._identities.values() if i.parent_id is None),
                key=lambda i: i.id,
            )
        )

    def validate(self) -> None:
        """Validate full registry integrity (parents, cycles, orphans)."""
        for identity in self._identities.values():
            if identity.parent_id is None:
                continue
            if identity.parent_id not in self._identities:
                msg = (
                    f"broken reference: {identity.id!r} parent "
                    f"{identity.parent_id!r} is unknown"
                )
                raise IndustryError(msg)
            self._assert_no_cycle(identity.id, identity.parent_id)

    def _assert_no_cycle(self, identity_id: str, parent_id: str) -> None:
        """Walk from parent toward root; fail if identity_id appears."""
        current_id: str | None = parent_id
        seen: set[str] = set()
        while current_id is not None:
            if current_id == identity_id:
                msg = (
                    f"circular hierarchy: registering {identity_id!r} under "
                    f"{parent_id!r}"
                )
                raise IndustryError(msg)
            if current_id in seen:
                msg = f"circular hierarchy detected at {current_id!r}"
                raise IndustryError(msg)
            seen.add(current_id)
            parent = self._identities.get(current_id)
            if parent is None:
                # Unknown parent is handled elsewhere at register time.
                return
            current_id = parent.parent_id
