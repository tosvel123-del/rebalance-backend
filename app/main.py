from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, validate_production_settings
from app.database import engine, Base
from app.api import auth, account, portfolio, notification, stock
from app.workers.scheduler import run_market_cycle
from hmac import compare_digest

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_production_settings()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(account.router)
app.include_router(portfolio.router)
app.include_router(notification.router)
app.include_router(stock.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}


@app.post("/internal/jobs/market-cycle")
async def market_cycle(x_job_secret: str | None = Header(default=None)):
    if not settings.JOB_TRIGGER_SECRET or not x_job_secret or not compare_digest(
        x_job_secret, settings.JOB_TRIGGER_SECRET
    ):
        raise HTTPException(status_code=401, detail="Invalid job trigger secret")
    ran = await run_market_cycle()
    return {"status": "completed" if ran else "already_running"}
