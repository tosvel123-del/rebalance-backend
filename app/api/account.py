from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth_utils import get_current_user, encrypt_secret, decrypt_secret
from app.database import get_db
from app.models.user import User, Account
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate

from app.services.kis_client import kis_client
import logging

router = APIRouter(prefix="/api/accounts", tags=["accounts"])
logger = logging.getLogger(__name__)

def mask_key(key: str) -> str:
    if len(key) <= 4:
        return "****"
    return key[:4] + "*" * (len(key) - 4)

@router.get("/holdings")
async def get_my_kis_holdings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Account).where(Account.user_id == current_user.id)
    res = await db.execute(stmt)
    acc = res.scalars().first()
    if not acc:
        return {"holdings": [], "account_no": None}

    try:
        app_key = decrypt_secret(acc.kis_app_key)
        app_secret = decrypt_secret(acc.kis_app_secret)
        holdings = await kis_client.get_account_holdings(app_key, app_secret, acc.account_no)
        return {"holdings": holdings, "account_no": acc.account_no}
    except Exception:
        logger.exception("KIS holdings sync failed for account id=%s", acc.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="KIS 잔고 조회에 실패했습니다. 앱키, 앱시크릿, 계좌번호와 Open API 권한을 확인하세요.",
        )

@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    acc_in: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Account).where(
        Account.user_id == current_user.id,
        Account.account_no == acc_in.account_no
    )
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Account already registered for this user")

    account = Account(
        user_id=current_user.id,
        label=acc_in.label,
        kis_app_key=encrypt_secret(acc_in.kis_app_key),
        kis_app_secret=encrypt_secret(acc_in.kis_app_secret),
        account_no=acc_in.account_no,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    acc_in: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    res = await db.execute(stmt)
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    duplicate_stmt = select(Account).where(
        Account.user_id == current_user.id,
        Account.account_no == acc_in.account_no,
        Account.id != account_id,
    )
    duplicate = await db.execute(duplicate_stmt)
    if duplicate.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Account already registered for this user")

    account.label = acc_in.label
    account.account_no = acc_in.account_no
    account.kis_app_key = encrypt_secret(acc_in.kis_app_key)
    account.kis_app_secret = encrypt_secret(acc_in.kis_app_secret)
    await db.commit()
    await db.refresh(account)
    return account

@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Account).where(Account.user_id == current_user.id)
    res = await db.execute(stmt)
    accounts = res.scalars().all()
    
    # Return accounts with masked keys for security
    response_list = []
    for acc in accounts:
        response_list.append(AccountResponse(
            id=acc.id,
            user_id=acc.user_id,
            label=acc.label,
            account_no=acc.account_no[:3] + "****" + acc.account_no[-2:] if len(acc.account_no) >= 5 else "*****",
            created_at=acc.created_at,
        ))
    return response_list

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    res = await db.execute(stmt)
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    await db.delete(account)
    await db.commit()
