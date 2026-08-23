from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth_utils import get_current_user, decrypt_secret
from app.database import get_db
from app.models.user import User, Account
from app.models.portfolio import Portfolio, Holding, TargetWeight
from app.schemas.portfolio import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse,
    HoldingsBatchUpdate, TargetWeightsBatchUpdate, PortfolioStatusResponse, RebalanceActionResponse
)
from app.services.price_service import price_service, StockReference
from app.services.rebalance_engine import RebalanceEngine
from app.services.kis_client import kis_client

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])
rebalance_engine = RebalanceEngine()

@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    p_in: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if p_in.account_id:
        acc_stmt = select(Account).where(Account.id == p_in.account_id, Account.user_id == current_user.id)
        res = await db.execute(acc_stmt)
        if not res.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Associated account not found")

    portfolio = Portfolio(
        user_id=current_user.id,
        account_id=p_in.account_id,
        name=p_in.name,
        cash_balance=p_in.cash_balance,
        threshold_pct=p_in.threshold_pct,
    )
    db.add(portfolio)
    await db.commit()

    stmt = select(Portfolio).options(
        selectinload(Portfolio.holdings),
        selectinload(Portfolio.target_weights)
    ).where(Portfolio.id == portfolio.id)
    res = await db.execute(stmt)
    return res.scalar_one()

@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Portfolio).options(
        selectinload(Portfolio.holdings),
        selectinload(Portfolio.target_weights)
    ).where(Portfolio.user_id == current_user.id)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Portfolio).options(
        selectinload(Portfolio.holdings),
        selectinload(Portfolio.target_weights)
    ).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    res = await db.execute(stmt)
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return p

@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: int,
    p_in: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Portfolio).options(
        selectinload(Portfolio.holdings),
        selectinload(Portfolio.target_weights)
    ).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    res = await db.execute(stmt)
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if p_in.name is not None:
        p.name = p_in.name
    if p_in.cash_balance is not None:
        p.cash_balance = p_in.cash_balance
    if p_in.threshold_pct is not None:
        p.threshold_pct = p_in.threshold_pct
    if p_in.is_rebalance_enabled is not None:
        p.is_rebalance_enabled = p_in.is_rebalance_enabled
    if p_in.is_notify_enabled is not None:
        p.is_notify_enabled = p_in.is_notify_enabled

    await db.commit()
    await db.refresh(p)
    return p

@router.put("/{portfolio_id}/holdings", response_model=PortfolioResponse)
async def update_holdings(
    portfolio_id: int,
    h_in: HoldingsBatchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    res = await db.execute(stmt)
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    await db.execute(delete(Holding).where(Holding.portfolio_id == portfolio_id))
    for item in h_in.holdings:
        holding = Holding(
            portfolio_id=portfolio_id,
            stock_code=item.stock_code,
            stock_name=item.stock_name,
            quantity=item.quantity,
            avg_price=item.avg_price,
            market=item.market,
        )
        db.add(holding)

    await db.commit()

    stmt = select(Portfolio).options(
        selectinload(Portfolio.holdings),
        selectinload(Portfolio.target_weights)
    ).where(Portfolio.id == portfolio_id)
    res = await db.execute(stmt)
    return res.scalar_one()

@router.put("/{portfolio_id}/targets", response_model=PortfolioResponse)
async def update_targets(
    portfolio_id: int,
    t_in: TargetWeightsBatchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    res = await db.execute(stmt)
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    await db.execute(delete(TargetWeight).where(TargetWeight.portfolio_id == portfolio_id))
    for item in t_in.targets:
        tw = TargetWeight(
            portfolio_id=portfolio_id,
            stock_code=item.stock_code,
            target_weight_pct=item.target_weight_pct,
            market=item.market,
        )
        db.add(tw)

    await db.commit()

    stmt = select(Portfolio).options(
        selectinload(Portfolio.holdings),
        selectinload(Portfolio.target_weights)
    ).where(Portfolio.id == portfolio_id)
    res = await db.execute(stmt)
    return res.scalar_one()

@router.post("/{portfolio_id}/sync", response_model=PortfolioResponse)
async def sync_kis_holdings(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Portfolio).options(selectinload(Portfolio.account)).where(
        Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id
    )
    res = await db.execute(stmt)
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if not p.account:
        raise HTTPException(status_code=400, detail="Portfolio is not linked to a KIS account")

    app_key = decrypt_secret(p.account.kis_app_key)
    app_secret = decrypt_secret(p.account.kis_app_secret)
    kis_holdings = await kis_client.get_account_holdings(app_key, app_secret, p.account.account_no)

    await db.execute(delete(Holding).where(Holding.portfolio_id == portfolio_id))
    for item in kis_holdings:
        holding = Holding(
            portfolio_id=portfolio_id,
            stock_code=item["stock_code"],
            stock_name=item["stock_name"],
            quantity=item["quantity"],
            avg_price=item["avg_price"],
            market="KR",
        )
        db.add(holding)

    await db.commit()

    stmt = select(Portfolio).options(
        selectinload(Portfolio.holdings),
        selectinload(Portfolio.target_weights)
    ).where(Portfolio.id == portfolio_id)
    res = await db.execute(stmt)
    return res.scalar_one()

@router.get("/{portfolio_id}/status", response_model=PortfolioStatusResponse)
async def get_portfolio_status(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Portfolio).options(
        selectinload(Portfolio.holdings),
        selectinload(Portfolio.target_weights),
        selectinload(Portfolio.account)
    ).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    res = await db.execute(stmt)
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    stocks = [StockReference(code=h.stock_code, name=h.stock_name, market=h.market) for h in p.holdings]
    prices = await price_service.get_prices_batch(stocks)

    total_val = rebalance_engine.calculate_total_value(p, prices)
    actions = rebalance_engine.check_portfolio(p, prices)

    action_responses = [
        RebalanceActionResponse(
            stock_code=a.stock_code,
            stock_name=a.stock_name,
            market=a.market,
            direction=a.direction,
            quantity=a.quantity,
            current_weight=a.current_weight,
            target_weight=a.target_weight,
            deviation=a.deviation,
            estimated_amount=a.estimated_amount,
            current_price=a.current_price,
        )
        for a in actions
    ]

    return PortfolioStatusResponse(
        portfolio_id=p.id,
        total_value=total_val,
        cash_balance=p.cash_balance,
        actions=action_responses,
    )
