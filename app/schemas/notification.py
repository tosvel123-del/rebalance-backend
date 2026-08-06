from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.notification import AlertStatus, TradeDirection

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    portfolio_id: int
    stock_code: str
    stock_name: str | None
    market: str
    direction: TradeDirection
    suggested_qty: int
    current_weight: Decimal
    target_weight: Decimal
    deviation: Decimal
    price_at_trigger: Decimal
    estimated_amount: Decimal
    status: AlertStatus
    fcm_message_id: str | None
    condition_cleared_at: datetime | None
    resolved_at: datetime | None
    sent_at: datetime

    class Config:
        from_attributes = True

class PendingAlertResponse(BaseModel):
    id: int
    user_id: int
    portfolio_id: int
    stock_code: str
    first_detected: datetime
    last_confirmed: datetime
    current_weight: Decimal
    target_weight: Decimal
    deviation: Decimal

    class Config:
        from_attributes = True
