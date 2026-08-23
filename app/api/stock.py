from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_utils import decrypt_secret, get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import Account, User
from app.services.kis_client import kis_client
from app.services.price_service import price_service
from app.services.price_service import StockReference
from pydantic import BaseModel

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

class StockPriceResponse(BaseModel):
    stock_code: str
    stock_name: str
    price: Decimal
    market: str
    source: str
    observed_at: str

@router.get("/price", response_model=StockPriceResponse)
async def get_stock_price(
    code: str = Query(..., description="Stock code, e.g. 005930"),
    name: str = Query("주식", description="Stock name for market classification"),
    market: str = Query("KR", description="KR for Korean listings, US for overseas symbols"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    normalized_market = "KR" if code.isdigit() and len(code) == 6 else market.upper()

    account = None
    if normalized_market == "KR":
        result = await db.execute(
            select(Account).where(Account.user_id == current_user.id).order_by(Account.id)
        )
        account = result.scalars().first()
        if not account:
            raise HTTPException(status_code=400, detail="KIS account is not linked")

    try:
        if normalized_market == "KR":
            price = await kis_client.get_domestic_price(
                decrypt_secret(account.kis_app_key),
                decrypt_secret(account.kis_app_secret),
                code,
            )
            return StockPriceResponse(
                stock_code=code,
                stock_name=name,
                price=price,
                market=normalized_market,
                source="kis_developers",
                observed_at=datetime.now(timezone.utc).isoformat(),
            )

        quote = await price_service.get_quote(
            StockReference(code=code, name=name, market=normalized_market)
        )
    except Exception as exc:
        if normalized_market != "KR" or not settings.ENABLE_NAVER_FALLBACK:
            raise HTTPException(status_code=502, detail="KIS market data is temporarily unavailable") from exc
        try:
            quote = await price_service.get_quote(
                StockReference(code=code, name=name, market=normalized_market)
            )
        except Exception as fallback_exc:
            raise HTTPException(status_code=502, detail="Market data is temporarily unavailable") from fallback_exc

    return StockPriceResponse(
        stock_code=code,
        stock_name=name,
        price=quote.price,
        market=normalized_market,
        source=quote.source,
        observed_at=quote.observed_at.isoformat(),
    )
