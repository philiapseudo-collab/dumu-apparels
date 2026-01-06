"""
PesaPal IPN (Instant Payment Notification) handler.

Processes IPN callbacks from PesaPal and updates order status.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import AsyncSessionLocal
from models import Order, User, ConversationLog
from services.pesapal_service import get_pesapal_payment_status
from services.chat_service import send_message

logger = logging.getLogger(__name__)


async def process_pesapal_ipn(
    order_tracking_id: str,
    merchant_reference: str
) -> None:
    """
    Process PesaPal IPN notification.
    
    Args:
        order_tracking_id: PesaPal order tracking ID
        merchant_reference: Merchant reference (ORDER_{order_id})
    """
    async with AsyncSessionLocal() as db:
        try:
            # Extract order ID from merchant reference (ORDER_123 -> 123)
            if not merchant_reference.startswith("ORDER_"):
                logger.warning(f"Invalid merchant reference format: {merchant_reference}")
                return
            
            order_id_str = merchant_reference.replace("ORDER_", "").strip()
            try:
                order_id = int(order_id_str)
            except ValueError:
                logger.error(f"Invalid order ID in merchant reference: {merchant_reference}")
                return
            
            # Find the order
            result = await db.execute(
                select(Order).where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                logger.error(f"Order {order_id} not found for IPN notification")
                return
            
            # Skip if already processed
            if order.status in ["paid", "failed"]:
                logger.info(f"Order {order_id} already processed with status {order.status}")
                return
            
            # Query PesaPal for payment status
            status_response = await get_pesapal_payment_status(order_tracking_id, merchant_reference)
            
            if not status_response:
                logger.error(f"Failed to get payment status for order {order_id}")
                return
            
            logger.info(f"PesaPal status response for order {order_id}: {status_response}")
            
            # Extract payment status from response
            # PesaPal API v3 might use different field names
            payment_status = (
                status_response.get("payment_status_description") or 
                status_response.get("status") or 
                status_response.get("payment_status") or 
                ""
            ).upper()
            payment_method = status_response.get("payment_method", "")
            
            logger.info(f"Order {order_id} payment status: {payment_status}, method: {payment_method}")
            
            # Update order based on payment status
            if payment_status == "COMPLETED":
                order.status = "paid"
                order.transaction_ref = order_tracking_id
                await db.commit()
                
                logger.info(f"Order {order_id} marked as paid via PesaPal")
                
                # Get user and send confirmation message
                user_result = await db.execute(
                    select(User).where(User.id == order.user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user:
                    confirmation_text = (
                        f"✅ Payment successful! 🎉\n\n"
                        f"Your order #{order.id} has been confirmed.\n\n"
                        f"Thank you for shopping with Dumu Apparels!"
                    )
                    
                    # Log confirmation
                    confirmation_log = ConversationLog(
                        user_id=user.id,
                        message=confirmation_text,
                        sender="bot"
                    )
                    db.add(confirmation_log)
                    await db.commit()
                    
                    # Send confirmation to user
                    await send_message(user.instagram_id, confirmation_text)
                    logger.info(f"Payment confirmation sent to user {user.instagram_id} for order {order_id}")
                
            elif payment_status in ["FAILED", "CANCELLED", "REJECTED"]:
                order.status = "failed"
                order.transaction_ref = order_tracking_id
                await db.commit()
                
                logger.info(f"Order {order_id} marked as failed via PesaPal (status: {payment_status})")
                
                # Optionally notify user of failure
                user_result = await db.execute(
                    select(User).where(User.id == order.user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user:
                    failure_text = (
                        f"❌ Payment was not successful.\n\n"
                        f"Your order #{order.id} could not be processed.\n\n"
                        f"Please try again or contact support if the issue persists."
                    )
                    
                    # Log failure notification
                    failure_log = ConversationLog(
                        user_id=user.id,
                        message=failure_text,
                        sender="bot"
                    )
                    db.add(failure_log)
                    await db.commit()
                    
                    await send_message(user.instagram_id, failure_text)
                    logger.info(f"Payment failure notification sent to user {user.instagram_id} for order {order_id}")
            else:
                # Status is PENDING or unknown - log but don't update
                logger.info(f"Order {order_id} still pending (status: {payment_status})")
                
        except Exception as e:
            logger.error(f"Error processing PesaPal IPN: {e}", exc_info=True)
            try:
                await db.rollback()
            except Exception:
                pass

