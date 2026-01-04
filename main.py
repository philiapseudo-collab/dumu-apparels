"""
Dumu Apparels - Instagram Bot Entry Point

FastAPI application for automating Instagram Direct Messages into
a high-conversion sales funnel for Kenyan online fashion brand.

Architecture: Hybrid (Rule-based for sales, AI for support)
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from config import get_settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting Dumu Apparels Instagram Bot...")
    try:
        # Validate configuration on startup
        settings = get_settings()
        logger.info(f"Configuration loaded: {settings.app_name} v{settings.app_version}")
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Dumu Apparels Instagram Bot...")


# Initialize FastAPI application
app = FastAPI(
    title="Dumu Apparels Instagram Bot",
    description="Automated Instagram DM sales funnel for Kenyan fashion brand",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """
    Root endpoint - Health check.
    
    Returns:
        JSONResponse: Application status and metadata
    """
    try:
        settings = get_settings()
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": settings.app_name,
                "version": settings.app_version,
                "message": "Dumu Apparels Instagram Bot is running"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": "Configuration validation failed",
                "message": str(e)
            }
        )


@app.get("/health")
async def health_check():
    """
    Dedicated health check endpoint.
    
    Returns:
        JSONResponse: Detailed health status
    """
    try:
        settings = get_settings()
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": settings.app_name,
                "version": settings.app_version,
                "currency": settings.currency,
                "payment_timeout_minutes": settings.payment_link_timeout
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )

