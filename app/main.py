from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1.router import api_v1_router
from .core.config import settings
from .core.logging import logger, setup_logging
from .services.aisstream_service import aisstream_service
from .services.vessel_cache_manager import vessel_cache_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    logger.info("Maritime AIS Provider: AISStream.io (https://aisstream.io)")

    if settings.AISSTREAM_API_KEY:
        masked_key = settings.AISSTREAM_API_KEY[:8] + "..." if len(settings.AISSTREAM_API_KEY) > 8 else "***"
        logger.info(f"AISStream API Key Configured: {masked_key}")
    else:
        logger.warning("AISStream API Key: Not Configured (Using baseline fallback)")

    # Ensure baseline data loaded
    vessel_cache_manager.ensure_baseline_loaded()

    # Start real-time AISStream WebSocket ingestion worker
    aisstream_service.start()

    yield

    # Shutdown
    logger.info("Shutting down backend services...")
    await aisstream_service.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI Backend for Langarnama Vessel Tracking - Powered by AISStream.io real-time marine stream",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for Vite & React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
async def root():
    """Root info and API discovery endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "provider": "aisstream.io",
        "docs": "/docs",
        "endpoints": {
            "ships": f"{settings.API_V1_STR}/ships",
            "ship_detail": f"{settings.API_V1_STR}/ships/{{ship_id}}",
            "ship_track": f"{settings.API_V1_STR}/ships/{{ship_id}}/track",
            "stream_status": f"{settings.API_V1_STR}/ships/stream/status",
            "ports": f"{settings.API_V1_STR}/ports",
            "stations": f"{settings.API_V1_STR}/stations",
            "stats": f"{settings.API_V1_STR}/stats",
            "websocket": f"{settings.API_V1_STR}/ws/live",
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check and AISStream connection status endpoint."""
    status = vessel_cache_manager.get_cache_status(
        aisstream_connected=aisstream_service.is_connected
    )
    status["aisstream_configured"] = bool(settings.AISSTREAM_API_KEY)
    status["aisstream_running"] = aisstream_service._running
    return status
