"""
Chat service for processing Instagram messages and sending responses.

Handles webhook event processing, user management, and message responses
using the Instagram Graph API.
"""

import httpx
import logging
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import get_settings
from database import AsyncSessionLocal
from models import User, ConversationLog, Product, Order
from services.pesapal_service import get_pesapal_payment_link
from services.kopokopo_service import KopoKopoService

logger = logging.getLogger(__name__)

KENYAN_MSISDN_LOCAL_RE = re.compile(r"^(07|01)\d{8}$")


def normalize_kenyan_phone_to_e164(local_msisdn: str) -> str:
    """
    Convert Kenyan local numbers like 0712345678 / 0112345678 to E.164.
    Example: 0712345678 -> +254712345678
    """
    msisdn = (local_msisdn or "").strip()
    if not KENYAN_MSISDN_LOCAL_RE.match(msisdn):
        raise ValueError("Invalid Kenyan phone number format")
    return f"+254{msisdn[1:]}"


async def send_message(recipient_id: str, text: str) -> bool:
    """
    Send a text message to an Instagram user via Graph API.
    
    Args:
        recipient_id: Instagram user ID to send message to
        text: Message text to send
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    settings = get_settings()
    url = "https://graph.facebook.com/v18.0/me/messages"
    
    # Strip any whitespace from token
    access_token = settings.page_access_token.strip()
    
    if not access_token:
        logger.error("PAGE_ACCESS_TOKEN is empty or not set")
        return False
    
    params = {
        "access_token": access_token
    }
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, params=params, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {recipient_id}")
                return True
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    error_code = error_data.get("error", {}).get("code", "Unknown")
                    logger.error(
                        f"Failed to send message to {recipient_id}. "
                        f"Status: {response.status_code}, Code: {error_code}, Message: {error_msg}"
                    )
                except:
                    logger.error(
                        f"Failed to send message to {recipient_id}. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                return False
                
    except Exception as e:
        logger.error(f"Error sending message to {recipient_id}: {e}", exc_info=True)
        return False


async def send_payment_link_button(recipient_id: str, payment_link: str, amount: float, product_name: str) -> bool:
    """
    Send a payment link as a button template (no logo/preview).
    
    Args:
        recipient_id: Instagram user ID to send message to
        payment_link: Payment URL
        amount: Payment amount
        product_name: Product name
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    settings = get_settings()
    url = "https://graph.facebook.com/v18.0/me/messages"
    
    # Strip any whitespace from token
    access_token = settings.page_access_token.strip()
    
    if not access_token:
        logger.error("PAGE_ACCESS_TOKEN is empty or not set")
        return False
    
    params = {
        "access_token": access_token
    }
    
    text = (
        f"Perfect! 💳\n\n"
        f"Complete your payment of KES {amount:,.2f} for {product_name}.\n\n"
        f"Click the button below to pay securely via Card (Visa/Mastercard)."
    )
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": [
                        {
                            "type": "web_url",
                            "url": payment_link,
                            "title": "Pay Now 💳"
                        }
                    ]
                }
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, params=params, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Payment link button sent successfully to {recipient_id}")
                return True
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    error_code = error_data.get("error", {}).get("code", "Unknown")
                    logger.error(
                        f"Failed to send payment link button to {recipient_id}. "
                        f"Status: {response.status_code}, Code: {error_code}, Message: {error_msg}"
                    )
                except:
                    logger.error(
                        f"Failed to send payment link button to {recipient_id}. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                return False
                
    except Exception as e:
        logger.error(f"Error sending payment link button to {recipient_id}: {e}", exc_info=True)
        return False


async def get_product_carousel(category: str, db: AsyncSession) -> list:
    """
    Query products by category and format them for Instagram Generic Template carousel.
    
    Args:
        category: Product category ('men' or 'women')
        db: Database session
        
    Returns:
        list: List of carousel elements (dicts with title, subtitle, image_url, buttons)
              Returns empty list if no products found (all exceptions propagate to caller)
    """
    # Query active products for the category, limit to 10
    result = await db.execute(
        select(Product)
        .where(Product.category == category.lower())
        .where(Product.is_active == True)
        .limit(10)
    )
    products = result.scalars().all()
    
    elements = []
    for product in products:
        # Skip products without image URLs
        if not product.image_url or not product.image_url.strip():
            logger.debug(f"Skipping product {product.id} ({product.name}) - no image URL")
            continue
        
        # Format price with commas
        price_str = f"KES {float(product.price):,.2f}"
        
        # Format sizes if available
        subtitle = price_str
        if product.sizes and len(product.sizes) > 0:
            sizes_str = ", ".join(str(size) for size in product.sizes)
            subtitle = f"{price_str} | Sizes: {sizes_str}"
        
        # Create carousel element
        element = {
            "title": product.name,
            "subtitle": subtitle,
            "image_url": product.image_url.strip(),
            "buttons": [
                {
                    "type": "postback",
                    "title": "Buy Now",
                    "payload": f"BUY_{product.id}"
                }
            ]
        }
        elements.append(element)
    
    return elements


async def send_carousel(recipient_id: str, elements: list) -> bool:
    """
    Send a Generic Template carousel to an Instagram user via Graph API.
    
    Args:
        recipient_id: Instagram user ID to send carousel to
        elements: List of carousel elements (each element is a dict with
                  title, subtitle, image_url, and buttons)
        
    Returns:
        bool: True if carousel sent successfully, False otherwise
    """
    settings = get_settings()
    url = "https://graph.facebook.com/v18.0/me/messages"
    
    # Strip any whitespace from token
    access_token = settings.page_access_token.strip()
    
    if not access_token:
        logger.error("PAGE_ACCESS_TOKEN is empty or not set")
        return False
    
    params = {
        "access_token": access_token
    }
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements
                }
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, params=params, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Carousel sent successfully to {recipient_id}")
                return True
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    error_code = error_data.get("error", {}).get("code", "Unknown")
                    logger.error(
                        f"Failed to send carousel to {recipient_id}. "
                        f"Status: {response.status_code}, Code: {error_code}, Message: {error_msg}"
                    )
                except:
                    logger.error(
                        f"Failed to send carousel to {recipient_id}. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                return False
                
    except Exception as e:
        logger.error(f"Error sending carousel to {recipient_id}: {e}", exc_info=True)
        return False


async def send_payment_selector(recipient_id: str, product: Product) -> bool:
    """
    Send a Button Template to allow user to select payment method.
    
    Args:
        recipient_id: Instagram user ID to send message to
        product: Product object with name and price
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    settings = get_settings()
    url = "https://graph.facebook.com/v18.0/me/messages"
    
    # Strip any whitespace from token
    access_token = settings.page_access_token.strip()
    
    if not access_token:
        logger.error("PAGE_ACCESS_TOKEN is empty or not set")
        return False
    
    params = {
        "access_token": access_token
    }
    
    # Format price with commas
    price_str = f"KES {float(product.price):,.2f}"
    text = f"Great choice! 👟 You are buying {product.name} for {price_str}.\n\nHow would you like to pay?"
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "M-Pesa (IntaSend)",
                            "payload": f"PAY_MPESA_{product.id}"
                        },
                        {
                            "type": "postback",
                            "title": "Card (PesaPal)",
                            "payload": f"PAY_CARD_{product.id}"
                        }
                    ]
                }
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, params=params, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Payment selector sent successfully to {recipient_id}")
                return True
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    error_code = error_data.get("error", {}).get("code", "Unknown")
                    logger.error(
                        f"Failed to send payment selector to {recipient_id}. "
                        f"Status: {response.status_code}, Code: {error_code}, Message: {error_msg}"
                    )
                except:
                    logger.error(
                        f"Failed to send payment selector to {recipient_id}. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                return False
                
    except Exception as e:
        logger.error(f"Error sending payment selector to {recipient_id}: {e}", exc_info=True)
        return False


async def _handle_showroom_request(recipient_id: str, category: str, user_id: int, db: AsyncSession) -> None:
    """
    Shared helper to handle showroom requests (fetch and send product carousel).
    
    Used by both text handlers ("men"/"women") and button handlers (SHOW_MEN/SHOW_WOMEN).
    
    Args:
        recipient_id: Instagram user ID to send message to
        category: Product category ('men' or 'women')
        user_id: User ID for logging
        db: Database session
    """
    # Normalize category to lowercase
    category_lower = category.lower().strip()
    
    try:
        elements = await get_product_carousel(category_lower, db)
        
        if elements:
            # Log carousel send attempt
            carousel_log = ConversationLog(
                user_id=user_id,
                message=f"[CAROUSEL] Showing {category_lower} products ({len(elements)} items)",
                sender="bot"
            )
            db.add(carousel_log)
            await db.commit()
            
            # Send carousel
            success = await send_carousel(recipient_id, elements)
            if success:
                logger.info(f"Carousel sent to {recipient_id} for category '{category_lower}'")
            else:
                logger.error(f"Failed to send carousel to {recipient_id}")
        else:
            # No products available
            no_stock_text = f"Sorry, no {category_lower} items in stock right now."
            no_stock_log = ConversationLog(
                user_id=user_id,
                message=no_stock_text,
                sender="bot"
            )
            db.add(no_stock_log)
            await db.commit()
            
            await send_message(recipient_id, no_stock_text)
            logger.info(f"No stock message sent to {recipient_id} for category '{category_lower}'")
            
    except Exception as e:
        logger.error(f"Error showing carousel for category '{category_lower}': {e}", exc_info=True)
        # Polite fallback message
        fallback_text = "We are having trouble loading the showroom. Please try again in a moment."
        fallback_log = ConversationLog(
            user_id=user_id,
            message=fallback_text,
            sender="bot"
        )
        db.add(fallback_log)
        await db.commit()
        
        await send_message(recipient_id, fallback_text)


async def send_welcome_menu(recipient_id: str) -> bool:
    """
    Send a Button Template welcome menu to allow user to choose a collection.
    
    Args:
        recipient_id: Instagram user ID to send message to
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    settings = get_settings()
    url = "https://graph.facebook.com/v18.0/me/messages"
    
    # Strip any whitespace from token
    access_token = settings.page_access_token.strip()
    
    if not access_token:
        logger.error("PAGE_ACCESS_TOKEN is empty or not set")
        return False
    
    params = {
        "access_token": access_token
    }
    
    text = "Welcome to Dumu Apparels! 🇰🇪\nWe have the best fits for you.\n\nChoose a collection to start shopping:"
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "Men's Collection 👟",
                            "payload": "SHOW_MEN"
                        },
                        {
                            "type": "postback",
                            "title": "Women's Collection 👗",
                            "payload": "SHOW_WOMEN"
                        }
                    ]
                }
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, params=params, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Welcome menu sent successfully to {recipient_id}")
                return True
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    error_code = error_data.get("error", {}).get("code", "Unknown")
                    logger.error(
                        f"Failed to send welcome menu to {recipient_id}. "
                        f"Status: {response.status_code}, Code: {error_code}, Message: {error_msg}"
                    )
                except:
                    logger.error(
                        f"Failed to send welcome menu to {recipient_id}. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                return False
                
    except Exception as e:
        logger.error(f"Error sending welcome menu to {recipient_id}: {e}", exc_info=True)
        return False


async def process_webhook_event(payload: dict) -> None:
    """
    Process incoming webhook event from Instagram.
    
    Handles message parsing, user management, and response generation.
    Runs in a background task with its own database session.
    
    Args:
        payload: Complete webhook payload from Meta/Instagram
    """
    # Create a new database session for this background task
    async with AsyncSessionLocal() as db:
        try:
            # Extract entry array
            entries = payload.get("entry", [])
            
            if not entries:
                logger.warning("Webhook payload has no entries")
                return
            
            # Process each entry
            for entry in entries:
                messaging_events = entry.get("messaging", [])
                
                for event in messaging_events:
                    # Skip status updates (delivery, read receipts)
                    if "delivery" in event or "read" in event:
                        logger.debug(f"Skipping status update: {event.keys()}")
                        continue
                    
                    # Extract sender ID (needed for both messages and postbacks)
                    sender = event.get("sender")
                    if not sender:
                        logger.warning("No sender in event")
                        continue
                    
                    sender_id = sender.get("id")
                    if not sender_id:
                        logger.warning("No sender ID in event")
                        continue
                    
                    # User Management: Find or create user (used by both messages and postbacks)
                    result = await db.execute(
                        select(User).where(User.instagram_id == sender_id)
                    )
                    user = result.scalar_one_or_none()
                    
                    if not user:
                        # Create new user
                        user = User(instagram_id=sender_id)
                        db.add(user)
                        await db.commit()
                        await db.refresh(user)
                        logger.info(f"New user created: {sender_id} (ID: {user.id})")
                    else:
                        logger.debug(f"Existing user: {sender_id} (ID: {user.id})")
                    
                    # Handle postbacks (button clicks)
                    if "postback" in event:
                        postback = event.get("postback")
                        payload = postback.get("payload", "") if postback else ""
                        
                        logger.info(f"Processing postback from {sender_id}: {payload}")
                        
                        # Log postback to ConversationLog
                        postback_log = ConversationLog(
                            user_id=user.id,
                            message=payload,
                            sender="user"
                        )
                        db.add(postback_log)
                        await db.commit()
                        
                        # Handle BUY_ payloads
                        if payload.startswith("BUY_"):
                            try:
                                # Extract product ID from payload (BUY_1 -> 1)
                                product_id_str = payload.replace("BUY_", "").strip()
                                product_id = int(product_id_str)
                                
                                # Fetch product from database
                                product_result = await db.execute(
                                    select(Product).where(Product.id == product_id)
                                )
                                product = product_result.scalar_one_or_none()
                                
                                # Validate product exists and is active
                                if not product or not product.is_active:
                                    error_text = "Sorry, this item is no longer available or out of stock."
                                    error_log = ConversationLog(
                                        user_id=user.id,
                                        message=error_text,
                                        sender="bot"
                                    )
                                    db.add(error_log)
                                    await db.commit()
                                    await send_message(sender_id, error_text)
                                    logger.warning(f"Product {product_id} not found or inactive for user {sender_id}")
                                    continue
                                
                                # Log the buy intent
                                buy_intent_log = ConversationLog(
                                    user_id=user.id,
                                    message=f"[BUTTON CLICK] Buy Now - Item {product_id}",
                                    sender="bot"
                                )
                                db.add(buy_intent_log)
                                await db.commit()
                                
                                # Send payment selector
                                success = await send_payment_selector(sender_id, product)
                                if success:
                                    payment_selector_log = ConversationLog(
                                        user_id=user.id,
                                        message="Payment selector displayed",
                                        sender="bot"
                                    )
                                    db.add(payment_selector_log)
                                    await db.commit()
                                    logger.info(f"Payment selector sent to {sender_id} for product {product_id}")
                                else:
                                    logger.error(f"Failed to send payment selector to {sender_id}")
                                    
                            except ValueError:
                                logger.error(f"Invalid product ID in payload: {payload}")
                                error_text = "Sorry, there was an error processing your request. Please try again."
                                await send_message(sender_id, error_text)
                            except Exception as e:
                                logger.error(f"Error processing BUY postback: {e}", exc_info=True)
                                error_text = "Sorry, there was an error processing your request. Please try again."
                                await send_message(sender_id, error_text)
                        
                        # Handle PAY_MPESA_ payloads
                        elif payload.startswith("PAY_MPESA_"):
                            try:
                                # Extract product ID from payload (PAY_MPESA_1 -> 1)
                                product_id_str = payload.replace("PAY_MPESA_", "").strip()
                                product_id = int(product_id_str)
                                
                                # Fetch and validate product
                                product_result = await db.execute(
                                    select(Product).where(Product.id == product_id)
                                )
                                product = product_result.scalar_one_or_none()
                                
                                # Validate product exists and is active
                                if not product or not product.is_active:
                                    error_text = "Sorry, this item is no longer available or out of stock."
                                    error_log = ConversationLog(
                                        user_id=user.id,
                                        message=error_text,
                                        sender="bot"
                                    )
                                    db.add(error_log)
                                    await db.commit()
                                    await send_message(sender_id, error_text)
                                    logger.warning(f"Product {product_id} not found or inactive for M-Pesa payment by user {sender_id}")
                                    continue
                                
                                # Log the payment method selection
                                payment_log = ConversationLog(
                                    user_id=user.id,
                                    message=f"[BUTTON CLICK] Selected M-Pesa - Item {product_id}",
                                    sender="bot"
                                )
                                db.add(payment_log)
                                await db.commit()

                                # Persist pending intent on the user so it survives restarts.
                                user.pending_product_id = product_id
                                await db.commit()

                                # If we don't have the user's phone number yet, ask for it.
                                if not user.phone_number:
                                    response_text = "Please reply with your M-Pesa number (e.g., 0712345678) to complete the payment."
                                    response_log = ConversationLog(
                                        user_id=user.id,
                                        message=response_text,
                                        sender="bot"
                                    )
                                    db.add(response_log)
                                    await db.commit()

                                    await send_message(sender_id, response_text)
                                    logger.info(f"Requested M-Pesa phone number from user {sender_id}")
                                    continue

                                # Normalize stored phone number to E.164 for Kopo Kopo.
                                try:
                                    e164_phone = normalize_kenyan_phone_to_e164(user.phone_number)
                                except Exception:
                                    # Stored number is invalid; ask again.
                                    user.phone_number = None
                                    await db.commit()
                                    response_text = "Please reply with your M-Pesa number (e.g., 0712345678) to complete the payment."
                                    await send_message(sender_id, response_text)
                                    continue

                                customer_email = f"instagram_{sender_id}@dumuapparels.local"
                                full_name = (user.name or "Instagram Customer").strip()
                                parts = [p for p in full_name.split(" ") if p]
                                first_name = parts[0] if parts else "Instagram"
                                last_name = " ".join(parts[1:]) if len(parts) > 1 else "Customer"
                                reference = f"IG_{sender_id}_PRODUCT_{product_id}"

                                kopokopo = KopoKopoService()
                                await kopokopo.initiate_stk_push(
                                    phone_number=e164_phone,
                                    amount=float(product.price),
                                    first_name=first_name,
                                    last_name=last_name,
                                    email=customer_email,
                                    reference=reference,
                                )

                                response_text = "I have sent a prompt to your phone! Please enter your PIN."
                                response_log = ConversationLog(
                                    user_id=user.id,
                                    message=response_text,
                                    sender="bot"
                                )
                                db.add(response_log)
                                await db.commit()

                                await send_message(sender_id, response_text)
                                logger.info(f"KopoKopo STK push initiated for user {sender_id}, product {product_id}")
                                    
                            except ValueError:
                                logger.error(f"Invalid product ID in payload: {payload}")
                                error_text = "Sorry, there was an error processing your request. Please try again."
                                await send_message(sender_id, error_text)
                            except Exception as e:
                                logger.error(f"Error processing PAY_MPESA postback: {e}", exc_info=True)
                                error_text = "Sorry, there was an error processing your request. Please try again."
                                await send_message(sender_id, error_text)
                        
                        # Handle PAY_CARD_ payloads
                        elif payload.startswith("PAY_CARD_"):
                            try:
                                # Extract product ID from payload (PAY_CARD_1 -> 1)
                                product_id_str = payload.replace("PAY_CARD_", "").strip()
                                product_id = int(product_id_str)
                                
                                # Fetch and validate product
                                product_result = await db.execute(
                                    select(Product).where(Product.id == product_id)
                                )
                                product = product_result.scalar_one_or_none()
                                
                                # Validate product exists and is active
                                if not product or not product.is_active:
                                    error_text = "Sorry, this item is no longer available or out of stock."
                                    error_log = ConversationLog(
                                        user_id=user.id,
                                        message=error_text,
                                        sender="bot"
                                    )
                                    db.add(error_log)
                                    await db.commit()
                                    await send_message(sender_id, error_text)
                                    logger.warning(f"Product {product_id} not found or inactive for Card payment by user {sender_id}")
                                    continue
                                
                                # Log the payment method selection
                                payment_log = ConversationLog(
                                    user_id=user.id,
                                    message=f"[BUTTON CLICK] Selected Card - Item {product_id}",
                                    sender="bot"
                                )
                                db.add(payment_log)
                                await db.commit()
                                
                                # Create order record
                                order = Order(
                                    user_id=user.id,
                                    product_id=product.id,
                                    amount=float(product.price),
                                    status="pending",
                                    payment_provider="pesapal"
                                )
                                db.add(order)
                                await db.commit()
                                await db.refresh(order)
                                
                                # Generate customer email from Instagram ID (since we don't collect emails yet)
                                customer_email = f"instagram_{sender_id}@dumuapparels.local"
                                customer_name = user.name or f"Customer {sender_id}"
                                
                                # Generate PesaPal payment link
                                payment_link = await get_pesapal_payment_link(
                                    amount=float(product.price),
                                    order_id=f"ORDER_{order.id}",
                                    customer_email=customer_email,
                                    customer_name=customer_name,
                                    phone_number=user.phone_number,
                                    product_name=product.name
                                )
                                
                                if payment_link:
                                    # Update order with transaction reference if available
                                    # PesaPal returns order_tracking_id which we can store
                                    # For now, we'll update it when we receive the IPN callback
                                    
                                    # Send payment link as button (no logo/preview)
                                    response_text = (
                                        f"Perfect! 💳\n\n"
                                        f"Complete your payment of KES {float(product.price):,.2f} for {product.name}.\n\n"
                                        f"Click the button below to pay securely via Card (Visa/Mastercard)."
                                    )
                                    
                                    response_log = ConversationLog(
                                        user_id=user.id,
                                        message=f"{response_text}\n\nPayment Link: {payment_link}",
                                        sender="bot"
                                    )
                                    db.add(response_log)
                                    await db.commit()
                                    
                                    success = await send_payment_link_button(
                                        sender_id, 
                                        payment_link, 
                                        float(product.price), 
                                        product.name
                                    )
                                    if success:
                                        logger.info(f"PesaPal payment link sent to user {sender_id}, order {order.id}")
                                    else:
                                        logger.error(f"Failed to send PesaPal payment link to {sender_id}")
                                else:
                                    # Failed to generate payment link
                                    error_text = "Sorry, we couldn't process your payment request at this time. Please try again later."
                                    error_log = ConversationLog(
                                        user_id=user.id,
                                        message=error_text,
                                        sender="bot"
                                    )
                                    db.add(error_log)
                                    await db.commit()
                                    
                                    # Mark order as failed
                                    order.status = "failed"
                                    await db.commit()
                                    
                                    await send_message(sender_id, error_text)
                                    logger.error(f"Failed to generate PesaPal payment link for user {sender_id}, order {order.id}")
                                    
                            except ValueError:
                                logger.error(f"Invalid product ID in payload: {payload}")
                                error_text = "Sorry, there was an error processing your request. Please try again."
                                await send_message(sender_id, error_text)
                            except Exception as e:
                                logger.error(f"Error processing PAY_CARD postback: {e}", exc_info=True)
                                error_text = "Sorry, there was an error processing your request. Please try again."
                                await send_message(sender_id, error_text)
                        
                        # Handle SHOW_MEN payload
                        elif payload == "SHOW_MEN":
                            try:
                                # Log the button click
                                click_log = ConversationLog(
                                    user_id=user.id,
                                    message="[BUTTON CLICK] View Collection - Men",
                                    sender="bot"
                                )
                                db.add(click_log)
                                await db.commit()
                                
                                # Call shared showroom handler
                                await _handle_showroom_request(sender_id, "men", user.id, db)
                                
                            except Exception as e:
                                logger.error(f"Error processing SHOW_MEN postback: {e}", exc_info=True)
                                error_text = "Sorry, there was an error processing your request. Please try again."
                                await send_message(sender_id, error_text)
                        
                        # Handle SHOW_WOMEN payload
                        elif payload == "SHOW_WOMEN":
                            try:
                                # Log the button click
                                click_log = ConversationLog(
                                    user_id=user.id,
                                    message="[BUTTON CLICK] View Collection - Women",
                                    sender="bot"
                                )
                                db.add(click_log)
                                await db.commit()
                                
                                # Call shared showroom handler
                                await _handle_showroom_request(sender_id, "women", user.id, db)
                                
                            except Exception as e:
                                logger.error(f"Error processing SHOW_WOMEN postback: {e}", exc_info=True)
                                error_text = "Sorry, there was an error processing your request. Please try again."
                                await send_message(sender_id, error_text)
                        
                        continue
                    
                    # Handle messages (text)
                    message = event.get("message")
                    if not message:
                        logger.warning(f"No message in event: {event.keys()}")
                        continue
                    
                    # Skip echo events (messages sent by the bot itself)
                    if message.get("is_echo", False):
                        logger.debug("Skipping echo event (bot's own message)")
                        continue
                    
                    # Extract text from message
                    text = message.get("text")
                    if not text:
                        logger.debug(f"Message has no text (might be attachment): {message.keys()}")
                        continue
                    
                    logger.info(f"Processing message from {sender_id}: {text}")
                    
                    # Log user message to ConversationLog
                    user_message_log = ConversationLog(
                        user_id=user.id,
                        message=text,
                        sender="user"
                    )
                    db.add(user_message_log)
                    await db.commit()
                    
                    # Response Rules (Hybrid Logic)
                    text_lower = text.lower().strip()

                    # Handle phone number input for M-Pesa (Kopo Kopo STK Push)
                    if KENYAN_MSISDN_LOCAL_RE.match(text_lower):
                        try:
                            e164_phone = normalize_kenyan_phone_to_e164(text_lower)
                        except Exception:
                            await send_message(sender_id, "Please send a valid M-Pesa number like 0712345678.")
                            continue

                        # Store local format (friendly) and keep it consistent with existing DB column size
                        user.phone_number = text_lower
                        await db.commit()

                        if user.pending_product_id:
                            product_result = await db.execute(
                                select(Product).where(Product.id == user.pending_product_id)
                            )
                            product = product_result.scalar_one_or_none()

                            if not product or not product.is_active:
                                user.pending_product_id = None
                                await db.commit()
                                await send_message(sender_id, "Sorry, that item is no longer available. Please choose another item.")
                                continue

                            customer_email = f"instagram_{sender_id}@dumuapparels.local"
                            full_name = (user.name or "Instagram Customer").strip()
                            parts = [p for p in full_name.split(" ") if p]
                            first_name = parts[0] if parts else "Instagram"
                            last_name = " ".join(parts[1:]) if len(parts) > 1 else "Customer"
                            reference = f"IG_{sender_id}_PRODUCT_{user.pending_product_id}"

                            kopokopo = KopoKopoService()
                            await kopokopo.initiate_stk_push(
                                phone_number=e164_phone,
                                amount=float(product.price),
                                first_name=first_name,
                                last_name=last_name,
                                email=customer_email,
                                reference=reference,
                            )

                            # Clear pending intent after initiating STK push
                            user.pending_product_id = None
                            await db.commit()

                            await send_message(sender_id, "I have sent a prompt to your phone! Please enter your PIN.")
                            logger.info(f"KopoKopo STK push initiated after phone capture for user {sender_id}")
                            continue

                        await send_message(sender_id, "Thanks! Your M-Pesa number has been saved. Tap M-Pesa again to pay.")
                        continue
                    
                    if text_lower in ["hi", "hello", "start"]:
                        # Send welcome menu
                        success = await send_welcome_menu(sender_id)
                        if success:
                            # Log welcome menu display
                            welcome_log = ConversationLog(
                                user_id=user.id,
                                message="Welcome menu displayed",
                                sender="bot"
                            )
                            db.add(welcome_log)
                            await db.commit()
                            logger.info(f"Welcome menu sent to {sender_id}")
                        else:
                            logger.error(f"Failed to send welcome menu to {sender_id}")
                    
                    elif text_lower in ["men", "women"]:
                        # Show product carousel for category (backward compatibility - text input)
                        await _handle_showroom_request(sender_id, text_lower, user.id, db)
                    
                    else:
                        # Default response (AI coming soon)
                        response_text = f"You said: {text}. (AI coming soon!)"
                        
                        # Log bot response to ConversationLog
                        bot_message_log = ConversationLog(
                            user_id=user.id,
                            message=response_text,
                            sender="bot"
                        )
                        db.add(bot_message_log)
                        await db.commit()
                        
                        # Send response message
                        success = await send_message(sender_id, response_text)
                        if success:
                            logger.info(f"Response sent to {sender_id}: {response_text[:50]}...")
                        else:
                            logger.error(f"Failed to send response to {sender_id}")
                    
        except Exception as e:
            logger.error(f"Error processing webhook event: {e}", exc_info=True)
            # Rollback on error
            try:
                await db.rollback()
            except Exception:
                pass

