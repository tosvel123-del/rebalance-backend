from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Numeric, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    threshold_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=3.00)
    is_rebalance_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_notify_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="portfolios")
    account = relationship("Account", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    target_weights = relationship("TargetWeight", back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("portfolio_id", "stock_code", name="uq_portfolio_stock"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    market: Mapped[str] = mapped_column(String(10), default="KR", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="holdings")


class TargetWeight(Base):
    __tablename__ = "target_weights"
    __table_args__ = (UniqueConstraint("portfolio_id", "stock_code", name="uq_portfolio_target_stock"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    target_weight_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    market: Mapped[str] = mapped_column(String(10), default="KR", nullable=False)

    portfolio = relationship("Portfolio", back_populates="target_weights")
