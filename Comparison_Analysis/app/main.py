from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from playwright.async_api import async_playwright

from app.config import settings
from app.core.llm import get_llm, get_fallback_llm, get_fallback_llm2, get_fallback_llm3
from app.core.openrouter import get_openrouter_llm, get_openrouter_vision_llm, get_openrouter_vision_fallback_llm
from app.core.tavily import TavilyWrapper
from app.core.duckduckgo import DuckDuckGoSearch
from app.core.cache import RedisClient
from app.scrapers.manager import ScraperManager
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import compare as compare_router
from app.routers import price_analysis as price_analysis_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Comparison service starting...")

    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
    app.state.pool = pool

    redis_client = RedisClient(settings.redis_url)
    await redis_client.init()
    await redis_client.delete_pattern("price:*")
    await redis_client.delete_pattern("compare:*")
    app.state.redis = redis_client

    app.state.llm = get_openrouter_llm()
    app.state.vision_llm = get_openrouter_vision_llm()
    app.state.vision_fallback_llm = get_openrouter_vision_fallback_llm()
    app.state.groq_llm = get_llm()
    app.state.groq_fallback_llm = get_fallback_llm()
    app.state.groq_fallback_llm2 = get_fallback_llm2()
    app.state.groq_fallback_llm3 = get_fallback_llm3()
    app.state.tavily = TavilyWrapper(settings.tavily_api_key)
    app.state.duckduckgo = DuckDuckGoSearch()
    app.state.report_cache = {}

    # ── Scraper infrastructure (Playwright browser) ──
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )
    app.state.playwright = playwright
    app.state.browser = browser
    app.state.scraper = ScraperManager(browser)

    logger.info("Comparison service ready")

    yield

    logger.info("Comparison service shutting down...")
    if app.state.redis:
        await app.state.redis.close()
    if pool:
        await pool.close()
    if app.state.browser:
        await app.state.browser.close()
    if app.state.playwright:
        await app.state.playwright.stop()


app = FastAPI(
    title="Cars Marketplace Comparison Analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(compare_router.router)
app.include_router(price_analysis_router.router)

Instrumentator().instrument(app).expose(app)
