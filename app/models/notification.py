import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class AlertStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"

class TradeDirection(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class PendingAlert(Base):
    __tablename__ = "pending_alerts"
    __table_args__ = (UniqueConstraint("portfolio_id", "stock_code", name="uq_pending_portfolio_stock"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    first_detected: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_confirmed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    current_weight: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    deviation: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market: Mapped[str] = mapped_column(String(10), default="KR", nullable=False)
    direction: Mapped[TradeDirection] = mapped_column(SQLEnum(TradeDirection), nullable=False)
    suggested_qty: Mapped[int] = mapped_column(nullable=False)
    current_weight: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    deviation: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    price_at_trigger: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False)
    fcm_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    condition_cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
