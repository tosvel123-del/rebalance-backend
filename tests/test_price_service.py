from datetime import datetime, timezone
from decimal import Decimal

import pytest

import app.services.price_service as price_service_module
from app.services.price_service import PriceQuote, PriceService, StockReference


class FakeProvider:
    source_name = "fake"

    def __init__(self):
        self.calls = 0

    async def get_quote(self, stock: StockReference) -> PriceQuote:
        self.calls += 1
        return PriceQuote(stock.code, Decimal("123.45"), self.source_name, datetime.now(timezone.utc))


class FakeCache:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        self.values[key] = value


@pytest.mark.asyncio
async def test_korean_listing_uses_korean_provider_and_cache(monkeypatch):
    monkeypatch.setattr(price_service_module, "redis_client", FakeCache())
    service = PriceService()
    provider = FakeProvider()
    service._providers["KR"] = provider

    quote = await service.get_quote(StockReference(code="005930", market="US"))
    cached_quote = await service.get_quote(StockReference(code="005930", market="US"))

    assert quote.price == Decimal("123.45")
    assert cached_quote.price == Decimal("123.45")
    assert provider.calls == 1
