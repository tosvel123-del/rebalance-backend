from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth_utils import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.notification import Notification, PendingAlert, AlertStatus
from app.schemas.notification import NotificationResponse, PendingAlertResponse

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    status: AlertStatus | None = Query(None),
    portfolio_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if status:
        stmt = stmt.where(Notification.status == status)
    if portfolio_id:
        stmt = stmt.where(Notification.portfolio_id == portfolio_id)
    stmt = stmt.order_by(Notification.sent_at.desc())

    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/pending", response_model=list[PendingAlertResponse])
async def list_pending_alerts(
    portfolio_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PendingAlert).where(PendingAlert.user_id == current_user.id)
    if portfolio_id:
        stmt = stmt.where(PendingAlert.portfolio_id == portfolio_id)

    res = await db.execute(stmt)
    return res.scalars().all()
