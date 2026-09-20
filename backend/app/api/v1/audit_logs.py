"""
backend/app/api/v1/audit_logs.py
================================
FastAPI Router for Enterprise Audit Log Querying & Compliance.
Exposes paginated, filterable database audit trail records.
"""

from typing import Annotated, List, Optional, Any
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.api.dependencies import get_current_user

router = APIRouter()


class AuditLogItem(BaseModel):
    id: str
    timestamp: str
    user_id: str
    user_email: str
    action: str
    category: str
    ip_address: str
    user_agent: str
    browser: str
    os: str
    status: str
    details: Optional[dict] = None
    execution_time_ms: int = 0


def _map_category(entity_type: str, action: str) -> str:
    """Derive standard high-level AuditCategory from entity_type and action."""
    action_upper = action.upper()
    entity_upper = entity_type.upper()

    if "AUTH" in action_upper or "LOGIN" in action_upper or "LOGOUT" in action_upper:
        return "AUTH"
    if "PREDICTION" in action_upper or "AI" in action_upper or entity_upper == "PREDICTION":
        return "AI"
    if "EVIDENCE" in action_upper or entity_upper == "EVIDENCE":
        return "EVIDENCE"
    if "INVESTIGATION" in action_upper or entity_upper == "INVESTIGATION":
        return "INVESTIGATION"
    if "USER" in action_upper:
        return "ADMIN"
    if entity_upper in ["CRIME_LOCATION", "CRIME_CATEGORY", "SYSTEM"]:
        return "ADMIN"
    return "ADMIN"


def _parse_agent(user_agent_str: Optional[str]) -> tuple[str, str]:
    """Extract browser and OS summary from User-Agent string."""
    if not user_agent_str:
        return "Unknown Browser", "Unknown OS"
    ua = user_agent_str.lower()
    browser = "Chrome" if "chrome" in ua else "Firefox" if "firefox" in ua else "Safari" if "safari" in ua else "API Client"
    os_name = "Windows" if "windows" in ua else "macOS" if "mac" in ua else "Linux" if "linux" in ua else "Other OS"
    return browser, os_name


@router.get(
    "",
    response_model=List[AuditLogItem],
    summary="Query Audit Logs",
    description="Returns filtered and paginated audit events from the immutable audit trail.",
)
async def get_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_current_user)] = None,
    search: Optional[str] = Query(default=None, description="Search keyword"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    status: Optional[str] = Query(default=None, description="Filter by status (SUCCESS, FAILURE, DENIED)"),
    limit: int = Query(default=50, ge=1, le=200, description="Max logs to return"),
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> Any:
    stmt = select(AuditLog).options(selectinload(AuditLog.user)).order_by(desc(AuditLog.created_at))

    if search:
        s = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                AuditLog.action.ilike(s),
                AuditLog.entity_type.ilike(s),
                AuditLog.ip_address.ilike(s),
            )
        )

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    items: List[AuditLogItem] = []
    for log in logs:
        details = log.details or {}
        log_status = details.get("status", "SUCCESS") if isinstance(details, dict) else "SUCCESS"
        exec_time = details.get("execution_time_ms", 0) if isinstance(details, dict) else 0

        cat = _map_category(log.entity_type, log.action)
        if category and category.upper() != "ALL" and cat != category.upper():
            continue

        if status and status.upper() != "ALL" and log_status.upper() != status.upper():
            continue

        user_email = log.user.email if log.user else (details.get("email") or "system@crimelens.ai")
        browser, os_name = _parse_agent(log.user_agent)

        items.append(
            AuditLogItem(
                id=str(log.id),
                timestamp=log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
                user_id=str(log.user_id) if log.user_id else "system",
                user_email=user_email,
                action=log.action,
                category=cat,
                ip_address=log.ip_address or "127.0.0.1",
                user_agent=log.user_agent or "Internal Service",
                browser=browser,
                os=os_name,
                status=log_status,
                details=details,
                execution_time_ms=exec_time,
            )
        )

    return items
