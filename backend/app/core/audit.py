from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def audit(db: AsyncSession, actor_id: str | None, action: str, entity: str,
                entity_id: str | None = None, meta: dict | None = None, ip: str | None = None) -> None:
    """Append an immutable audit row. ``ip`` is accepted for call-site clarity but
    is not stored because the audit table only keeps the before/after payload."""
    db.add(AuditLog(
        actor_id=actor_id, action=action, entity=entity,
        entity_id=entity_id or "", before=None, after=meta,
    ))
