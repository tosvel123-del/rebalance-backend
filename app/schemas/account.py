from datetime import datetime
from pydantic import BaseModel

class AccountCreate(BaseModel):
    label: str = "KIS Account"
    kis_app_key: str
    kis_app_secret: str
    account_no: str

class AccountResponse(BaseModel):
    id: int
    user_id: int
    label: str
    account_no: str
    created_at: datetime

    class Config:
        from_attributes = True
