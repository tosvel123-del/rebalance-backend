from decimal import Decimal

import pytest

import app.services.kis_client as kis_client_module
from app.services.kis_client import KISClient


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "output1": [
                {
                    "pdno": "005930",
                    "prdt_name": "삼성전자",
                    "hldg_qty": "3",
                    "pchs_avg_pric": "71234.5000",
                    "prpr": "73400",
                }
            ]
        }


class FakeAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, *args, **kwargs):
        return FakeResponse()


@pytest.mark.asyncio
async def test_holdings_use_kis_average_and_current_price(monkeypatch):
    client = KISClient()

    async def fake_token(*args, **kwargs):
        return "token"

    monkeypatch.setattr(client, "get_access_token", fake_token)
    monkeypatch.setattr(kis_client_module.httpx, "AsyncClient", FakeAsyncClient)

    holdings = await client.get_account_holdings("key", "secret", "1234567801")

    assert holdings == [
        {
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "quantity": 3,
            "avg_price": Decimal("71234.5000"),
            "current_price": Decimal("73400"),
        }
    ]
