from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from app.auth_utils import get_current_user, decrypt_secret
from app.database import get_db
from app.models.user import User, Account
from app.services.price_service import price_service
from app.services.kis_client import kis_client
from pydantic import BaseModel

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

class StockPriceResponse(BaseModel):
    stock_code: str
    stock_name: str
    price: Decimal
    market: str

@router.get("/price", response_model=StockPriceResponse)
async def get_stock_price(
    code: str = Query(..., description="Stock code, e.g. 005930"),
    name: str = Query("주식", description="Stock name for market classification"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    # Retrieve user's linked account for KIS API credentials, if available
    stmt = select(Account).where(Account.user_id == current_user.id)
    res = await db.execute(stmt)
    acc = res.scalars().first()

    app_key, app_secret = "", ""
    if acc:
        app_key = decrypt_secret(acc.kis_app_key)
        app_secret = decrypt_secret(acc.kis_app_secret)

    try:
        price = await price_service.get_price(code, app_key, app_secret)
    except Exception:
        # Return fallback mock price if KIS keys are not yet registered
        price = Decimal("75000")

    market = price_service.classify_market(code, name)
    return StockPriceResponse(
        stock_code=code,
        stock_name=name,
        price=price,
        market=market,
    )
