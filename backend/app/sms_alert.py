"""
SMS Notification Module — Smart Shelf Vision AI
────────────────────────────────────────────────
Sends SMS alerts to the store owner when stock goes below 5.
Uses Twilio if configured; otherwise falls back to printing
the message to the backend console (safe for student demos).

Configuration:
  Set these environment variables (or edit the defaults below):
    TWILIO_ACCOUNT_SID  — Your Twilio Account SID
    TWILIO_AUTH_TOKEN   — Your Twilio Auth Token
    TWILIO_PHONE_FROM   — Your Twilio phone number (e.g., +1234567890)
    OWNER_PHONE_NUMBER  — Store owner's phone (e.g., +91XXXXXXXXXX)
"""

import os
import logging

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────
# You can set these as environment variables or edit the defaults directly.
TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM  = os.getenv("TWILIO_PHONE_FROM", "")
OWNER_PHONE  = os.getenv("OWNER_PHONE_NUMBER", "+919999999999")  # <-- Change to real number

# Track which products we have already alerted about (avoid spamming)
_alerted_products: set = set()


def _twilio_available() -> bool:
    """Check if Twilio credentials are configured."""
    return bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM)


def send_low_stock_sms(product_name: str, current_stock: int):
    """
    Send an SMS to the store owner about low stock.
    
    This function is called automatically by the inventory_logic module
    whenever a product's stock falls below 5 units.
    
    ► If Twilio is configured → sends a real SMS.
    ► If not configured       → prints to backend console (safe fallback).
    
    The function also tracks which products have already been alerted
    to prevent sending duplicate messages for the same product.
    """
    # Avoid duplicate alerts for the same product
    if product_name in _alerted_products:
        return
    
    _alerted_products.add(product_name)

    # Build message
    message_body = (
        f"🚨 SmartShelf Alert!\n\n"
        f"Product: {product_name}\n"
        f"Current Stock: {current_stock} units\n"
        f"Status: {'OUT OF STOCK' if current_stock <= 0 else 'LOW STOCK'}\n\n"
        f"Please restock immediately.\n"
        f"— SmartShelf Vision AI"
    )

    if _twilio_available():
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            msg = client.messages.create(
                body=message_body,
                from_=TWILIO_FROM,
                to=OWNER_PHONE,
            )
            logger.info(f"[SMS] Sent low-stock alert for '{product_name}' → {OWNER_PHONE} (SID: {msg.sid})")
            print(f"[SMS ✅] Alert sent to {OWNER_PHONE} for '{product_name}' (stock: {current_stock})")
        except Exception as e:
            logger.error(f"[SMS] Failed to send alert: {e}")
            print(f"[SMS ❌] Failed to send to {OWNER_PHONE}: {e}")
            # Print to console as fallback
            print(f"[SMS FALLBACK] Message:\n{message_body}")
    else:
        # No Twilio configured — print to console for demo purposes
        print("\n" + "=" * 55)
        print("📱  SMS ALERT (Simulated — Twilio not configured)")
        print("=" * 55)
        print(f"  To:      {OWNER_PHONE}")
        print(f"  Message: {message_body}")
        print("=" * 55 + "\n")


def reset_alert(product_name: str):
    """
    Called when a product is restocked above the threshold.
    Removes it from the alerted set so a future low-stock event
    will trigger a new SMS.
    """
    _alerted_products.discard(product_name)
