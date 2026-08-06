import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.portfolio import Portfolio
from app.auth_utils import decrypt_secret
from app.services.price_service import price_service
from app.services.rebalance_engine import RebalanceEngine
from app.services.notification_service import notification_service

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
rebalance_engine = RebalanceEngine()

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

            app_key, app_secret = "", ""
            if p.account:
                app_key = decrypt_secret(p.account.kis_app_key)
                app_secret = decrypt_secret(p.account.kis_app_secret)

            codes = [h.stock_code for h in p.holdings]
            prices = await price_service.get_prices_batch(codes, app_key, app_secret)

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
            app_key, app_secret = "", ""
            if p.account:
                app_key = decrypt_secret(p.account.kis_app_key)
                app_secret = decrypt_secret(p.account.kis_app_secret)

            codes = [h.stock_code for h in p.holdings]
            prices = await price_service.get_prices_batch(codes, app_key, app_secret)
            actions = rebalance_engine.check_portfolio(p, prices)

            # Check ACTIVE alerts resolution status (15 min delay)
            await notification_service.check_active_alerts(session, p.id, actions)

def start_scheduler():
    # Schedule every 1 min during stock market hours (09:00 - 15:30)
    scheduler.add_job(
        run_price_check,
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="*",
        id="price_check_job",
        replace_existing=True
    )
    # Lifecycle check extends to 15:45 for post-market resolution
    scheduler.add_job(
        run_alert_lifecycle,
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="*",
        id="alert_lifecycle_job",
        replace_existing=True
    )
    scheduler.start()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start_scheduler()
    print("Background worker scheduler started.")
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
