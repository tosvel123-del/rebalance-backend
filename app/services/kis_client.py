from decimal import Decimal
import httpx
from fastapi import HTTPException
from app.redis_client import redis_client

class KISClient:
    BASE_URL = "https://openapi.koreainvestment.com:9443"

    async def get_access_token(self, app_key: str, app_secret: str) -> str:
        cache_key = f"kis_token:{app_key}"
        try:
            cached_token = await redis_client.get(cache_key)
            if cached_token:
                return cached_token
        except Exception:
            pass

        url = f"{self.BASE_URL}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "appsecret": app_secret,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="KIS OAuth token generation failed")

            data = resp.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in", 86400)

            try:
                await redis_client.set(cache_key, access_token, ex=max(60, expires_in - 60))
            except Exception:
                pass

            return access_token

    async def get_domestic_price(self, app_key: str, app_secret: str, stock_code: str) -> Decimal:
        token = await self.get_access_token(app_key, app_secret)
        url = f"{self.BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "FHKST01010100",
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=10.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to fetch price for {stock_code}")

            data = resp.json()
            stck_prpr = data.get("output", {}).get("stck_prpr")
            if not stck_prpr:
                raise HTTPException(status_code=400, detail=f"Invalid price response for {stock_code}")

            return Decimal(stck_prpr)

    async def get_account_holdings(self, app_key: str, app_secret: str, account_no: str) -> list[dict]:
        token = await self.get_access_token(app_key, app_secret)
        url = f"{self.BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"

        # KIS account format: CANO (8 digits) + ACNT_PRDT_CD (2 digits)
        cano = account_no[:8]
        acnt_prdt_cd = account_no[8:] if len(account_no) > 8 else "01"

        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "TTTC8434R",
        }
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFLD_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FCP_AMNT_ICLD_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=10.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch KIS account balance")

            data = resp.json()
            output1 = data.get("output1", [])
            holdings = []
            for item in output1:
                qty = int(item.get("hldg_qty", 0))
                if qty > 0:
                    holdings.append({
                        "stock_code": item.get("pdno"),
                        "stock_name": item.get("prdt_name"),
                        "quantity": qty,
                        "avg_price": Decimal(item.get("pavr", 0)),
                    })
            return holdings

    async def get_overseas_price(self, app_key: str, app_secret: str, market: str, stock_code: str) -> Decimal:
        raise NotImplementedError("Direct overseas stock API is reserved for future implementation.")

kis_client = KISClient()
