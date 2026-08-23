from datetime import datetime
from pydantic import BaseModel, Field


class AccountInput(BaseModel):
    label: str = "KIS Account"
    kis_app_key: str = Field(min_length=1)
    kis_app_secret: str = Field(min_length=1)
    account_no: str = Field(pattern=r"^\d{10}$")


class AccountCreate(AccountInput):
    pass


class AccountUpdate(AccountInput):
    pass

class AccountResponse(BaseModel):
    id: int
    user_id: int
    label: str
    account_no: str
    created_at: datetime

    class Config:
        from_attributes = True
