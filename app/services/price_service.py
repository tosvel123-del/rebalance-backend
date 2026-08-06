from decimal import Decimal
from app.redis_client import redis_client
from app.services.kis_client import kis_client

class PriceService:
    CACHE_TTL = 30  # 30 seconds

    US_ETF_KEYWORDS = ["S&P500", "나스닥", "NASDAQ", "미국", "빅테크", "US", "NYSE"]

    def classify_market(self, stock_code: str, stock_name: str) -> str:
        """Classify as 'US' if stock name indicates US-tracked domestic ETF, otherwise 'KR'."""
        name_upper = stock_name.upper()
        if any(keyword.upper() in name_upper for keyword in self.US_ETF_KEYWORDS):
            return "US"
        return "KR"

    async def get_price(self, stock_code: str, app_key: str, app_secret: str) -> Decimal:
        cache_key = f"stock_price:{stock_code}"
        try:
            cached_price = await redis_client.get(cache_key)
            if cached_price:
                return Decimal(cached_price)
        except Exception:
            pass

        price = await kis_client.get_domestic_price(app_key, app_secret, stock_code)
        try:
            await redis_client.set(cache_key, str(price), ex=self.CACHE_TTL)
        except Exception:
            pass
        return price

    async def get_prices_batch(self, stock_codes: list[str], app_key: str, app_secret: str) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for code in stock_codes:
            try:
                result[code] = await self.get_price(code, app_key, app_secret)
            except Exception:
                pass
        return result

price_service = PriceService()
