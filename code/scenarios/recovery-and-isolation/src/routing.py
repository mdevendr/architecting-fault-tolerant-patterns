"""Stable tenant-to-cell assignment with explicit dedicated-cell overrides."""

from __future__ import annotations

import hashlib


def assign_cell(
    tenant_id: str,
    cells: tuple[str, ...],
    dedicated_assignments: dict[str, str] | None = None,
) -> str:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    if not cells:
        raise ValueError("at least one cell is required")
    dedicated_assignments = dedicated_assignments or {}
    if tenant_id in dedicated_assignments:
        assigned = dedicated_assignments[tenant_id]
        if assigned not in cells:
            raise ValueError(f"dedicated assignment references unknown cell: {assigned}")
        return assigned
    digest = hashlib.sha256(tenant_id.encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], byteorder="big") % len(cells)
    return cells[index]


def ordering_key(tenant_id: str, business_entity_id: str) -> str:
    """Return the declared ordering boundary; do not append a random UUID."""
    if not tenant_id or not business_entity_id:
        raise ValueError("tenant_id and business_entity_id are required")
    return f"{tenant_id}#{business_entity_id}"

