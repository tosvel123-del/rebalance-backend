from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth_utils import get_current_user
from app.models.user import User
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
):
    try:
        quote = await price_service.get_quote(StockReference(code=code, name=name, market=market))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Market data is temporarily unavailable") from exc

    return StockPriceResponse(
        stock_code=code,
        stock_name=name,
        price=quote.price,
        market=market.upper(),
        source=quote.source,
        observed_at=quote.observed_at.isoformat(),
    )
