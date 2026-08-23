import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.portfolio import Portfolio
from app.services.price_service import price_service, StockReference
from app.services.rebalance_engine import RebalanceEngine
from app.services.notification_service import notification_service

rebalance_engine = RebalanceEngine()
market_cycle_lock = asyncio.Lock()

async def run_price_check():
    async with AsyncSessionLocal() as session:
        stmt = select(Portfolio).options(
            selectinload(Portfolio.holdings),
            selectinload(Portfolio.target_weights),
            selectinload(Portfolio.account),
            selectinload(Portfolio.user)
        ).where(Portfolio.is_active.is_(True))
        res = await session.execute(stmt)
        portfolios = res.scalars().all()

        for p in portfolios:
            if not p.holdings:
                continue

            stocks = [StockReference(code=h.stock_code, name=h.stock_name, market=h.market) for h in p.holdings]
            prices = await price_service.get_prices_batch(stocks)

            actions = rebalance_engine.check_portfolio(p, prices)

            # Process 10-minute sustain condition & pending alerts
            await notification_service.process_deviations(session, p.user_id, p.id, actions)
            await notification_service.promote_matured_pendings(session, p.user, p.id, actions)

async def run_alert_lifecycle():
    async with AsyncSessionLocal() as session:
        stmt = select(Portfolio).options(
            selectinload(Portfolio.holdings),
            selectinload(Portfolio.account)
        ).where(Portfolio.is_active.is_(True))
        res = await session.execute(stmt)
        portfolios = res.scalars().all()

        for p in portfolios:
            stocks = [StockReference(code=h.stock_code, name=h.stock_name, market=h.market) for h in p.holdings]
            prices = await price_service.get_prices_batch(stocks)
            actions = rebalance_engine.check_portfolio(p, prices)

            # Check ACTIVE alerts resolution status (15 min delay)
            await notification_service.check_active_alerts(session, p.id, actions)

async def run_market_cycle() -> bool:
    """Run by a single authenticated external scheduler request."""
    if market_cycle_lock.locked():
        return False

    async with market_cycle_lock:
        await run_price_check()
        await run_alert_lifecycle()
    return True

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    print("Run this module through the authenticated job endpoint.")
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
