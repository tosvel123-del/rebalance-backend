from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth_utils import get_current_user, encrypt_secret, decrypt_secret
from app.database import get_db
from app.models.user import User, Account
from app.schemas.account import AccountCreate, AccountResponse

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

def mask_key(key: str) -> str:
    if len(key) <= 4:
        return "****"
    return key[:4] + "*" * (len(key) - 4)

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

    # Safety Guard: Check if key appears to be a trade/write key
    if "TRADE" in acc_in.kis_app_key.upper() or "WRITE" in acc_in.kis_app_key.upper():
        raise HTTPException(status_code=400, detail="Read-Only (Quotation) API key required. Write/Trade keys are forbidden.")

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
