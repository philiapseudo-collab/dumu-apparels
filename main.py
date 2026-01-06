"""
Dumu Apparels - Instagram Bot Entry Point

FastAPI application for automating Instagram Direct Messages into
a high-conversion sales funnel for Kenyan online fashion brand.

Architecture: Hybrid (Rule-based for sales, AI for support)
"""

from fastapi import FastAPI, Query, Body, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, Response, HTMLResponse, PlainTextResponse
from contextlib import asynccontextmanager
from config import get_settings
from pathlib import Path
from services.chat_service import process_webhook_event
from services.pesapal_ipn import process_pesapal_ipn
from services.pesapal_service import register_pesapal_ipn
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


@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Meta/Instagram webhook verification endpoint (Hub Challenge).
    
    This endpoint is called by Meta during webhook setup to verify
    that the webhook URL is valid and belongs to the application.
    
    Args:
        request: FastAPI Request object to extract query parameters
        
    Returns:
        Response: Plain text challenge string if verification succeeds
        
    Raises:
        HTTPException: 403 if verification fails, 400 if parameters missing
    """
    # Extract query parameters (Meta uses hub.mode, hub.verify_token, hub.challenge)
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    logger.info(f"Verifying webhook: mode={mode}, token={token}")
    
    # Check if all required parameters are present
    if not mode or not token or not challenge:
        logger.warning(f"Webhook verification failed: Missing required parameters")
        raise HTTPException(
            status_code=400,
            detail="Missing required parameters: hub.mode, hub.verify_token, hub.challenge"
        )
    
    settings = get_settings()
    
    # Verify mode is "subscribe"
    if mode != "subscribe":
        logger.warning(f"Webhook verification failed: Invalid mode '{mode}' (expected 'subscribe')")
        raise HTTPException(
            status_code=403,
            detail="Verification failed: Invalid mode"
        )
    
    # Verify token matches
    if token != settings.verify_token:
        logger.warning(f"Webhook verification failed: Token mismatch (received token does not match VERIFY_TOKEN)")
        raise HTTPException(
            status_code=403,
            detail="Verification failed"
        )
    
    # Verification successful
    logger.info(f"Webhook verification successful: challenge={challenge}")
    return Response(content=challenge, media_type="text/plain")


@app.post("/webhook")
async def receive_webhook(
    payload: dict = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Meta/Instagram webhook ingestion endpoint.
    
    Receives all events from Instagram (messages, postbacks, etc.)
    and processes them in the background. Returns 200 OK immediately to
    prevent webhook timeouts.
    
    Args:
        payload: Complete webhook payload from Meta/Instagram
        background_tasks: FastAPI BackgroundTasks for async processing
        
    Returns:
        dict: {"status": "received"} to acknowledge receipt immediately
    """
    logger.info(f"Received Event: {payload}")
    
    # Add processing to background tasks
    # This ensures we return 200 OK immediately without waiting
    background_tasks.add_task(process_webhook_event, payload)
    
    # Return immediately to prevent Meta timeout
    return {"status": "received"}


@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy():
    """Privacy Policy page for Meta app requirements."""
    policy_path = Path("privacy-policy.html")
    if policy_path.exists():
        return policy_path.read_text(encoding="utf-8")
    return HTMLResponse(
        content="<h1>Privacy Policy</h1><p>Privacy policy page not found.</p>",
        status_code=404
    )


@app.get("/terms-of-service", response_class=HTMLResponse)
async def terms_of_service():
    """Terms of Service page for Meta app requirements."""
    terms_path = Path("terms-of-service.html")
    if terms_path.exists():
        return terms_path.read_text(encoding="utf-8")
    return HTMLResponse(
        content="<h1>Terms of Service</h1><p>Terms of service page not found.</p>",
        status_code=404
    )


@app.get("/data-deletion", response_class=HTMLResponse)
async def data_deletion():
    """Data Deletion Instructions page for Meta app requirements."""
    deletion_path = Path("data-deletion.html")
    if deletion_path.exists():
        return deletion_path.read_text(encoding="utf-8")
    return HTMLResponse(
        content="<h1>Data Deletion</h1><p>Data deletion page not found.</p>",
        status_code=404
    )


@app.get("/pesapal/ipn/info")
async def pesapal_ipn_info():
    """
    Get information about the PesaPal IPN endpoint URL.
    
    Returns the IPN URL that should be registered in PesaPal dashboard.
    """
    settings = get_settings()
    base_url = settings.base_url or "https://your-domain.com"  # User should set this in .env
    
    ipn_url = f"{base_url.rstrip('/')}/pesapal/ipn"
    
    return JSONResponse(content={
        "ipn_url": ipn_url,
        "endpoint": "/pesapal/ipn",
        "method": "GET",
        "instructions": (
            "1. Set BASE_URL in .env file to your production domain\n"
            "2. Copy the ipn_url above\n"
            "3. Register it in your PesaPal Merchant Dashboard under IPN Settings\n"
            "4. Or use POST /pesapal/ipn/register to register programmatically"
        ),
        "note": "The IPN URL must be publicly accessible via HTTPS"
    })


@app.post("/pesapal/ipn/register")
async def pesapal_ipn_register(ipn_url: str = Body(..., embed=True)):
    """
    Register an IPN URL with PesaPal programmatically.
    
    Args:
        ipn_url: The full URL where PesaPal should send IPN notifications
                 (e.g., https://yourdomain.com/pesapal/ipn)
        
    Returns:
        JSON response with IPN notification ID
    """
    ipn_id = await register_pesapal_ipn(ipn_url)
    
    if ipn_id:
        return JSONResponse(content={
            "success": True,
            "ipn_id": ipn_id,
            "ipn_url": ipn_url,
            "message": f"IPN URL registered successfully. Save this IPN ID: {ipn_id}"
        })
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to register IPN URL with PesaPal. Check logs for details."
        )


@app.get("/pesapal/ipn")
async def pesapal_ipn(
    pesapal_notification_type: str = Query(...),
    pesapal_transaction_tracking_id: str = Query(...),
    pesapal_merchant_reference: str = Query(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    PesaPal IPN (Instant Payment Notification) callback endpoint.
    
    PesaPal sends GET requests to this endpoint when payment status changes.
    We must echo back the parameters to acknowledge receipt, then process
    the payment status update in the background.
    
    Args:
        pesapal_notification_type: Notification type (typically "CHANGE")
        pesapal_transaction_tracking_id: PesaPal transaction tracking ID
        pesapal_merchant_reference: Merchant reference (ORDER_{order_id})
        background_tasks: FastAPI BackgroundTasks for async processing
        
    Returns:
        PlainTextResponse: Echoed parameters as required by PesaPal
    """
    logger.info(
        f"PesaPal IPN received: type={pesapal_notification_type}, "
        f"tracking_id={pesapal_transaction_tracking_id}, "
        f"reference={pesapal_merchant_reference}"
    )
    
    # Echo back the parameters as required by PesaPal
    response_text = (
        f"pesapal_notification_type={pesapal_notification_type}&"
        f"pesapal_transaction_tracking_id={pesapal_transaction_tracking_id}&"
        f"pesapal_merchant_reference={pesapal_merchant_reference}"
    )
    
    # Process the IPN in the background (after responding to PesaPal)
    background_tasks.add_task(
        process_pesapal_ipn,
        pesapal_transaction_tracking_id,
        pesapal_merchant_reference
    )
    
    # Return immediately with echoed parameters (required by PesaPal)
    return PlainTextResponse(content=response_text, status_code=200)


@app.get("/payment/callback")
async def payment_callback(
    OrderTrackingId: str = Query(None, alias="OrderTrackingId"),
    OrderMerchantReference: str = Query(None, alias="OrderMerchantReference")
):
    """
    Payment callback endpoint - redirects users back to Instagram after payment.
    
    PesaPal redirects users here after payment completion. We redirect them
    back to Instagram's direct inbox.
    
    Args:
        OrderTrackingId: PesaPal order tracking ID (optional)
        OrderMerchantReference: Merchant reference (optional)
        
    Returns:
        RedirectResponse: Redirects to Instagram
    """
    from fastapi.responses import RedirectResponse
    
    logger.info(
        f"Payment callback received - OrderTrackingId: {OrderTrackingId}, "
        f"OrderMerchantReference: {OrderMerchantReference}"
    )
    
    # Redirect to Instagram's direct inbox
    # This will open Instagram app if installed, or open Instagram web in browser
    instagram_url = "https://www.instagram.com/direct/inbox/"
    
    # For mobile apps, use deep link (will open Instagram app if installed)
    # The web URL will work for both web and mobile browsers
    return RedirectResponse(url=instagram_url, status_code=302)


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

