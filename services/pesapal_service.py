"""
PesaPal payment service for processing card payments.

Handles payment link generation and order creation for PesaPal payments.
"""

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from config import get_settings

logger = logging.getLogger(__name__)


async def register_pesapal_ipn(ipn_url: str) -> Optional[str]:
    """
    Register an IPN URL with PesaPal and get the IPN notification ID.
    
    Args:
        ipn_url: The full URL where PesaPal should send IPN notifications
                 (e.g., https://yourdomain.com/pesapal/ipn)
        
    Returns:
        str: IPN notification ID if successful, None otherwise
    """
    settings = get_settings()
    
    # PesaPal API v3 IPN registration endpoint - Production
    url = "https://pay.pesapal.com/v3/api/URLSetup/RegisterIPN"
    
    # Get access token first
    access_token = await get_pesapal_access_token()
    if not access_token:
        logger.error("Failed to get PesaPal access token for IPN registration")
        return None
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    payload = {
        "url": ipn_url,
        "ipn_notification_type": "GET"  # PesaPal sends GET requests to IPN endpoint
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                ipn_id = data.get("ipn_id")
                if ipn_id:
                    logger.info(f"PesaPal IPN URL registered successfully: {ipn_url} (IPN ID: {ipn_id})")
                    return ipn_id
                else:
                    logger.error(f"PesaPal IPN registration response missing ipn_id: {data}")
                    return None
            else:
                logger.error(
                    f"Failed to register PesaPal IPN URL. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return None
                
    except Exception as e:
        logger.error(f"Error registering PesaPal IPN URL: {e}", exc_info=True)
        return None


async def get_pesapal_access_token() -> Optional[str]:
    """
    Get PesaPal access token using consumer key and secret.
    
    Returns:
        str: Access token if successful, None otherwise
    """
    settings = get_settings()
    
    # Validate credentials are set
    if not settings.pesapal_consumer_key or not settings.pesapal_consumer_secret:
        logger.error(
            "PesaPal credentials not configured. Please set PESAPAL_CONSUMER_KEY and "
            "PESAPAL_CONSUMER_SECRET environment variables."
        )
        return None
    
    # Log first few characters for debugging (without exposing full credentials)
    key_prefix = settings.pesapal_consumer_key[:8] + "..." if len(settings.pesapal_consumer_key) > 8 else "***"
    logger.debug(f"Attempting PesaPal authentication with consumer_key: {key_prefix}")
    
    # PesaPal API v3 endpoints - Production
    url = "https://pay.pesapal.com/v3/api/Auth/RequestToken"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # PesaPal API v3 RequestToken endpoint requires credentials in JSON body
    payload = {
        "consumer_key": settings.pesapal_consumer_key,
        "consumer_secret": settings.pesapal_consumer_secret
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                if token:
                    logger.info("PesaPal access token retrieved successfully")
                    return token
                else:
                    # Check if response contains error information
                    error_info = data.get("error", {})
                    error_code = error_info.get("code", "unknown")
                    error_message = error_info.get("message", "")
                    
                    if error_code == "invalid_consumer_key_or_secret_provided":
                        logger.error(
                            "PesaPal authentication failed: Invalid consumer key or secret. "
                            "Please verify your PESAPAL_CONSUMER_KEY and PESAPAL_CONSUMER_SECRET "
                            "in Railway environment variables match your PesaPal Merchant Dashboard credentials."
                        )
                    else:
                        logger.error(f"PesaPal token response missing token field: {data}")
                    return None
            else:
                try:
                    error_data = response.json()
                    error_info = error_data.get("error", {})
                    error_code = error_info.get("code", "unknown")
                    
                    if error_code == "invalid_consumer_key_or_secret_provided":
                        logger.error(
                            f"PesaPal authentication failed (HTTP {response.status_code}): "
                            f"Invalid consumer key or secret. Please verify your credentials in Railway."
                        )
                    else:
                        logger.error(
                            f"Failed to get PesaPal access token. "
                            f"Status: {response.status_code}, Response: {response.text}"
                        )
                except Exception:
                    logger.error(
                        f"Failed to get PesaPal access token. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                return None
                
    except Exception as e:
        logger.error(f"Error getting PesaPal access token: {e}", exc_info=True)
        return None


async def create_pesapal_order(
    amount: float,
    order_id: str,
    customer_email: str,
    customer_name: str,
    phone_number: Optional[str] = None,
    description: str = "Purchase from Dumu Apparels",
    callback_url: Optional[str] = None,
    notification_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a PesaPal order and get payment link.
    
    Args:
        amount: Payment amount in KES
        order_id: Unique order identifier
        customer_email: Customer email address
        customer_name: Customer full name
        phone_number: Customer phone number (optional)
        description: Order description
        callback_url: URL to redirect after payment (optional for Instagram bot)
        notification_id: IPN notification ID (optional)
        
    Returns:
        dict: Response containing order_tracking_id and redirect_url if successful, None otherwise
    """
    settings = get_settings()
    
    # Get access token
    access_token = await get_pesapal_access_token()
    if not access_token:
        logger.error("Failed to get PesaPal access token")
        return None
    
    # PesaPal API v3 submit order endpoint - Production
    url = "https://pay.pesapal.com/v3/api/Transactions/SubmitOrderRequest"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    # Build customer data
    customer_data = {
        "email_address": customer_email,
        "phone_number": phone_number or "",
        "first_name": customer_name.split()[0] if customer_name else "",
        "last_name": " ".join(customer_name.split()[1:]) if customer_name and len(customer_name.split()) > 1 else customer_name or ""
    }
    
    payload = {
        "id": order_id,
        "currency": settings.currency,
        "amount": amount,
        "description": description,
        "callback_url": callback_url or "",
        "redirect_mode": "",
        "branch": "",
        "billing_address": {
            "email_address": customer_email,
            "phone_number": phone_number or "",
            "country_code": "KE",
            "first_name": customer_data["first_name"],
            "last_name": customer_data["last_name"]
        }
    }
    
    # Only include notification_id if it's provided (PesaPal rejects empty strings)
    if notification_id:
        payload["notification_id"] = notification_id
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # PesaPal may return errors in response body even with 200 status
                if "error" in data:
                    error_info = data.get("error", {})
                    error_code = error_info.get("code", "unknown")
                    error_message = error_info.get("message", "")
                    logger.error(
                        f"PesaPal order creation failed (HTTP 200 but error in response). "
                        f"Code: {error_code}, Message: {error_message}, Response: {data}"
                    )
                    return None
                logger.info(f"PesaPal order created successfully: {order_id}")
                return data
            else:
                logger.error(
                    f"Failed to create PesaPal order. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return None
                
    except Exception as e:
        logger.error(f"Error creating PesaPal order: {e}", exc_info=True)
        return None


async def get_pesapal_payment_link(
    amount: float,
    order_id: str,
    customer_email: str,
    customer_name: str,
    phone_number: Optional[str] = None,
    product_name: Optional[str] = None
) -> Optional[str]:
    """
    Generate a PesaPal payment link for an order.
    
    Args:
        amount: Payment amount in KES
        order_id: Unique order identifier
        customer_email: Customer email address
        customer_name: Customer full name
        phone_number: Customer phone number (optional)
        product_name: Product name for description (optional)
        
    Returns:
        str: Payment URL if successful, None otherwise
    """
    settings = get_settings()
    description = f"Payment for {product_name}" if product_name else "Purchase from Dumu Apparels"
    
    # PesaPal requires a callback URL. For Instagram bots, this is where users are redirected after payment.
    # Use BASE_URL if available, otherwise use a placeholder (PesaPal requires a valid URL format)
    if settings.base_url:
        callback_url = f"{settings.base_url.rstrip('/')}/payment/callback"
    else:
        # Use a placeholder URL - PesaPal requires a valid URL format
        # In production, BASE_URL should be set to your actual domain
        callback_url = "https://dumuapparels.com/payment/callback"
    
    result = await create_pesapal_order(
        amount=amount,
        order_id=order_id,
        customer_email=customer_email,
        customer_name=customer_name,
        phone_number=phone_number,
        description=description,
        callback_url=callback_url
    )
    
    if result:
        # PesaPal API v3 returns redirect_url in the response
        redirect_url = result.get("redirect_url")
        if redirect_url:
            return redirect_url
        else:
            logger.error(f"PesaPal response missing redirect_url: {result}")
            return None
    
    return None


async def get_pesapal_payment_status(order_tracking_id: str, order_id: str) -> Optional[Dict[str, Any]]:
    """
    Query PesaPal for payment status using order tracking ID.
    
    Args:
        order_tracking_id: PesaPal order tracking ID
        order_id: Merchant order ID
        
    Returns:
        dict: Payment status response if successful, None otherwise
    """
    settings = get_settings()
    
    # Get access token
    access_token = await get_pesapal_access_token()
    if not access_token:
        logger.error("Failed to get PesaPal access token for status query")
        return None
    
    # PesaPal API v3 get transaction status endpoint - Production
    url = f"https://pay.pesapal.com/v3/api/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"PesaPal payment status retrieved for order {order_id}")
                return data
            else:
                logger.error(
                    f"Failed to get PesaPal payment status. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return None
                
    except Exception as e:
        logger.error(f"Error getting PesaPal payment status: {e}", exc_info=True)
        return None

