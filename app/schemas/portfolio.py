from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class HoldingItem(BaseModel):
    stock_code: str
    stock_name: str
    quantity: int = Field(ge=0)
    avg_price: Decimal | None = None
    market: str = "KR"

class TargetWeightItem(BaseModel):
    stock_code: str
    target_weight_pct: Decimal = Field(ge=0, le=100)
    market: str = "KR"

class PortfolioCreate(BaseModel):
    name: str
    account_id: int | None = None
    cash_balance: Decimal = Decimal("0")
    threshold_pct: Decimal = Decimal("3.00")

class PortfolioUpdate(BaseModel):
    name: str | None = None
    cash_balance: Decimal | None = None
    threshold_pct: Decimal | None = None
    is_rebalance_enabled: bool | None = None
    is_notify_enabled: bool | None = None

class HoldingsBatchUpdate(BaseModel):
    holdings: list[HoldingItem]

class TargetWeightsBatchUpdate(BaseModel):
    targets: list[TargetWeightItem]

class HoldingResponse(HoldingItem):
    id: int
    portfolio_id: int

    class Config:
        from_attributes = True

class TargetWeightResponse(TargetWeightItem):
    id: int
    portfolio_id: int

    class Config:
        from_attributes = True

class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    account_id: int | None = None
    name: str
    cash_balance: Decimal
    threshold_pct: Decimal
    is_rebalance_enabled: bool
    is_notify_enabled: bool
    is_active: bool
    created_at: datetime
    holdings: list[HoldingResponse] = []
    target_weights: list[TargetWeightResponse] = []

    class Config:
        from_attributes = True

class RebalanceActionResponse(BaseModel):
    stock_code: str
    stock_name: str
    market: str
    direction: str
    quantity: int
    current_weight: Decimal
    target_weight: Decimal
    deviation: Decimal
    estimated_amount: Decimal
    current_price: Decimal

class PortfolioStatusResponse(BaseModel):
    portfolio_id: int
    total_value: Decimal
    cash_balance: Decimal
    actions: list[RebalanceActionResponse]
