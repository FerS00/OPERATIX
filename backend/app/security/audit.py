"""Safe audit recording with explicit redaction boundaries."""

from sqlalchemy.orm import Session

from backend.app.models.security import AuditLog


def record_audit(
    session: Session,
    *,
    user_id: str | None,
    action: str,
    tool: str | None,
    parameters_summary: str = "",
    result: str,
    status: str,
) -> None:
    """Stage a bounded audit entry; callers decide when to commit."""
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            tool=tool,
            parameters_summary=parameters_summary[:2_000],
            result=result[:100],
            status=status[:30],
        )
    )
