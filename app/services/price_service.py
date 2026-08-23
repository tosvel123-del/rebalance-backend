import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

import httpx

from app.config import settings
from app.redis_client import redis_client


@dataclass(frozen=True)
class StockReference:
    code: str
    name: str = ""
    market: str = "KR"


@dataclass(frozen=True)
class PriceQuote:
    code: str
    price: Decimal
    source: str
    observed_at: datetime


class MarketDataProvider(Protocol):
    source_name: str

    async def get_quote(self, stock: StockReference) -> PriceQuote: ...


class NaverFinanceProvider:
    """Small wrapper around Naver Finance's undocumented read-only endpoint."""

    source_name = "naver_finance"
    _url = "https://polling.finance.naver.com/api/realtime"

    async def get_quote(self, stock: StockReference) -> PriceQuote:
        headers = {"User-Agent": "rebalance-notify/1.0"}
        params = {"query": f"SERVICE_ITEM:{stock.code}"}
        async with httpx.AsyncClient(headers=headers, timeout=8.0) as client:
            response = await client.get(self._url, params=params)
            response.raise_for_status()

        record = self._find_matching_record(response.json(), stock.code)
        if not record:
            raise ValueError(f"Naver Finance returned no quote for {stock.code}")

        raw_price = next(
            (record.get(key) for key in ("nv", "closePrice", "currentPrice") if record.get(key) is not None),
            None,
        )
        if raw_price is None:
            raise ValueError(f"Naver Finance returned no price for {stock.code}")
        return PriceQuote(
            code=stock.code,
            price=Decimal(str(raw_price).replace(",", "")),
            source=self.source_name,
            observed_at=datetime.now(timezone.utc),
        )

    def _find_matching_record(self, value: object, code: str) -> dict | None:
        if isinstance(value, dict):
            if str(value.get("cd", value.get("code", ""))) == code:
                return value
            for child in value.values():
                found = self._find_matching_record(child, code)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = self._find_matching_record(child, code)
                if found:
                    return found
        return None


class YahooFinanceProvider:
    """Optional provider for overseas symbols used by small personal deployments."""

    source_name = "yahoo_finance"

    async def get_quote(self, stock: StockReference) -> PriceQuote:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("yfinance is not installed") from exc

        def fetch_last_close() -> Decimal:
            history = yf.Ticker(stock.code).history(period="5d", interval="1d")
            if history.empty:
                raise ValueError(f"Yahoo Finance returned no quote for {stock.code}")
            return Decimal(str(history["Close"].iloc[-1]))

        price = await asyncio.to_thread(fetch_last_close)
        return PriceQuote(
            code=stock.code,
            price=price,
            source=self.source_name,
            observed_at=datetime.now(timezone.utc),
        )


class PriceService:
    """Provider selection and cache policy kept independent from portfolio accounts."""

    def __init__(self) -> None:
        self._providers: dict[str, MarketDataProvider] = {
            "KR": NaverFinanceProvider(),
            "US": YahooFinanceProvider(),
        }

    def _provider_for(self, stock: StockReference) -> MarketDataProvider:
        # Six-digit symbols are Korean listings, including locally listed overseas ETFs.
        market = "KR" if stock.code.isdigit() and len(stock.code) == 6 else stock.market.upper()
        return self._providers.get(market, self._providers["US"])

    async def get_quote(self, stock: StockReference) -> PriceQuote:
        provider = self._provider_for(stock)
        cache_key = f"stock_price:{provider.source_name}:{stock.code}"
        try:
            cached = await redis_client.get(cache_key)
        except Exception:
            cached = None
        if cached:
            payload = json.loads(cached)
            return PriceQuote(
                code=stock.code,
                price=Decimal(payload["price"]),
                source=payload["source"],
                observed_at=datetime.fromisoformat(payload["observed_at"]),
            )

        quote = await provider.get_quote(stock)
        try:
            await redis_client.set(
                cache_key,
                json.dumps(
                    {
                        "price": str(quote.price),
                        "source": quote.source,
                        "observed_at": quote.observed_at.isoformat(),
                    }
                ),
                ex=settings.PRICE_CACHE_TTL_SECONDS,
            )
        except Exception:
            pass
        return quote

    async def get_price(self, code: str, name: str = "", market: str = "KR") -> Decimal:
        """Compatibility helper for one-off price reads."""
        return (await self.get_quote(StockReference(code=code, name=name, market=market))).price

    async def get_prices_batch(self, stocks: list[StockReference]) -> dict[str, Decimal]:
        quotes = await asyncio.gather(*(self.get_quote(stock) for stock in stocks), return_exceptions=True)
        return {
            quote.code: quote.price
            for quote in quotes
            if isinstance(quote, PriceQuote)
        }


price_service = PriceService()
