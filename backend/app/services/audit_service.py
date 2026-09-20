"""
AuditService
============
Centralised audit-logging helper.

Every Create / Update / Delete operation in the service layer must call
AuditService.log() so all data mutations are permanently traceable.

Captured fields
---------------
user_id       UUID of the authenticated actor.
entity_type   Model name string  (e.g. "CrimeCategory").
entity_id     UUID of the affected database row.
action        Verb string: "CREATE" | "UPDATE" | "DELETE".
details       Optional JSON blob (before/after values, changed fields, etc.).
ip_address    Extracted from the FastAPI Request — respects X-Forwarded-For
              for deployments behind a reverse proxy or load balancer.
user_agent    Extracted from the User-Agent request header.

Transaction ownership
---------------------
AuditService.log() does NOT commit the session.  It only flushes the new
AuditLog row so the row is part of the same transaction as the parent
service operation.  The parent service method calls db.commit() once,
atomically persisting both the business entity change and the audit record.
This guarantees that audit logs are never created for transactions that
ultimately fail.
"""
import uuid
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.audit_log import AuditLog


class AuditService:
    """Namespace for audit-logging helpers (stateless — all methods are static)."""

    @staticmethod
    async def log(
        db: AsyncSession,
        user_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        details: Optional[dict] = None,
        request: Optional[Request] = None,
    ) -> None:
        """
        Persist a single AuditLog record inside the current DB session.

        Parameters
        ----------
        db          Active async SQLAlchemy session.
        user_id     UUID of the actor performing the action.
        entity_type Human-readable model name (e.g. "CrimeReport").
        entity_id   Primary key of the affected record.
        action      "CREATE", "UPDATE", or "DELETE".
        details     Optional dict serialised to JSONB in PostgreSQL.
        request     FastAPI Request object used to extract IP / User-Agent.
                    Pass None in unit tests or background tasks.
        """
        ip_address: Optional[str] = None
        user_agent: Optional[str] = None

        if request is not None:
            # Respect reverse-proxy header so the real client IP is captured
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip_address = forwarded_for.split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host

            user_agent = request.headers.get("User-Agent")

        audit_entry = AuditLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_entry)

        # flush() makes the row part of the current transaction without
        # committing — the parent service method commits everything together.
        await db.flush()

        logger.info(
            "AUDIT | action=%-8s | entity=%s:%s | user=%s | ip=%s",
            action,
            entity_type,
            entity_id,
            user_id,
            ip_address,
        )
