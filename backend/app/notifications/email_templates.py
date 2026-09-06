import html
from datetime import datetime

def escape_html(val) -> str:
    if val is None:
        return ""
    return html.escape(str(val))

def render_stock_alert_email(
    product_name: str,
    current_stock: int,
    threshold: int,
    alert_type: str = "LOW_STOCK",
    shelf_name: str = "Unassigned",
    category: str = "General",
    sku: str = "N/A",
    timestamp: str = None
) -> tuple[str, str, str]:
    """
    Renders subject, html_content, and text_content for stock alerts.
    alert_type can be 'LOW_STOCK' or 'OUT_OF_STOCK'.
    """
    now_str = timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    clean_product = escape_html(product_name)
    clean_category = escape_html(category)
    clean_sku = escape_html(sku or "N/A")
    clean_shelf = escape_html(shelf_name or "Shelf Main")

    is_out = (alert_type == "OUT_OF_STOCK") or (current_stock <= 0)
    
    if is_out:
        subject = f"[CRITICAL] Out of Stock Alert: {clean_product} (0 remaining)"
        header_badge = "OUT OF STOCK"
        header_color = "#dc2626"  # Red
        bg_accent = "#fef2f2"
        border_accent = "#f87171"
        action_text = "Urgent: Immediate restocking required. This item is completely depleted from shelves."
    else:
        subject = f"[ALERT] Low Stock Warning: {clean_product} ({current_stock} remaining / min {threshold})"
        header_badge = "LOW STOCK WARNING"
        header_color = "#ea580c"  # Orange
        bg_accent = "#fff7ed"
        border_accent = "#fb923c"
        action_text = f"Notice: Stock has reached or fallen below minimum threshold ({threshold} units). Please schedule replenishment."

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0f172a; padding: 30px 10px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
          <!-- Top Brand Banner -->
          <tr>
            <td style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%); padding: 24px 30px; text-align: left;">
              <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;">
                SmartShelf Vision AI
              </h1>
              <p style="margin: 4px 0 0 0; font-size: 13px; color: #e0e7ff; font-weight: 500;">
                Automated Computer Vision Inventory Intelligence
              </p>
            </td>
          </tr>

          <!-- Alert Status Header -->
          <tr>
            <td style="padding: 24px 30px 12px 30px;">
              <div style="display: inline-block; background-color: {bg_accent}; border: 1px solid {border_accent}; color: {header_color}; font-weight: 700; font-size: 12px; padding: 5px 12px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">
                {header_badge}
              </div>
              <h2 style="margin: 0 0 8px 0; font-size: 20px; color: #f8fafc; font-weight: 700;">
                Inventory Alert: {clean_product}
              </h2>
              <p style="margin: 0; font-size: 14px; color: #94a3b8; line-height: 1.5;">
                {action_text}
              </p>
            </td>
          </tr>

          <!-- Metrics Table -->
          <tr>
            <td style="padding: 12px 30px 20px 30px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0f172a; border-radius: 8px; border: 1px solid #334155; border-collapse: separate; overflow: hidden;">
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8; font-size: 13px; font-weight: 600; width: 40%;">Product</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #f8fafc; font-size: 14px; font-weight: 700;">{clean_product}</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8; font-size: 13px; font-weight: 600;">Current Stock</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: {header_color}; font-size: 18px; font-weight: 800;">{current_stock} units</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8; font-size: 13px; font-weight: 600;">Threshold Limit</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #cbd5e1; font-size: 14px; font-weight: 600;">{threshold} units</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8; font-size: 13px; font-weight: 600;">Shelf Location</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #cbd5e1; font-size: 14px;">{clean_shelf}</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #94a3b8; font-size: 13px; font-weight: 600;">Category / SKU</td>
                  <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #cbd5e1; font-size: 14px;">{clean_category} (SKU: {clean_sku})</td>
                </tr>
                <tr>
                  <td style="padding: 12px 16px; color: #94a3b8; font-size: 13px; font-weight: 600;">Validated At</td>
                  <td style="padding: 12px 16px; color: #94a3b8; font-size: 13px;">{now_str}</td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- System Note -->
          <tr>
            <td style="padding: 0 30px 24px 30px;">
              <div style="background-color: rgba(99, 102, 241, 0.08); border-left: 3px solid #6366f1; padding: 12px 16px; border-radius: 0 6px 6px 0;">
                <p style="margin: 0; font-size: 12px; color: #a5b4fc; line-height: 1.4;">
                  <strong>AI Verification Verified:</strong> This notification was dispatched after multi-frame ByteTrack &amp; YOLO inventory confirmation in the database. Raw camera occlusions do not trigger alerts.
                </p>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #0b1120; padding: 20px 30px; text-align: center; border-top: 1px solid #334155;">
              <p style="margin: 0 0 6px 0; font-size: 12px; color: #64748b;">
                SmartShelf Vision AI System &bull; Automated Real-Time Notifications
              </p>
              <p style="margin: 0; font-size: 11px; color: #475569;">
                You are receiving this alert because your email is registered as an authorized inventory manager.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    text_content = f"""[SMARTSHELF VISION AI - INVENTORY ALERT]
Status: {header_badge}
Product: {product_name}
Current Stock: {current_stock}
Threshold: {threshold}
Shelf Location: {shelf_name}
Category: {category} (SKU: {sku})
Validated Timestamp: {now_str}

Action Required:
{action_text}

---
This alert was verified via SmartShelf multi-frame tracking.
"""
    return subject, html_content, text_content


def render_test_email(recipient: str, timestamp: str = None) -> tuple[str, str, str]:
    """
    Renders subject, html_content, and text_content for system test email.
    """
    now_str = timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    clean_recipient = escape_html(recipient)
    subject = "[TEST] SmartShelf Vision AI - Email Notification System Connected"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0f172a; padding: 30px 10px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
          <tr>
            <td style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 24px 30px; text-align: left;">
              <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: #ffffff;">
                SmartShelf Vision AI
              </h1>
              <p style="margin: 4px 0 0 0; font-size: 13px; color: #d1fae5; font-weight: 500;">
                SMTP Email Integration &bull; Test Delivery
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding: 24px 30px;">
              <div style="display: inline-block; background-color: #ecfdf5; border: 1px solid #34d399; color: #059669; font-weight: 700; font-size: 12px; padding: 5px 12px; border-radius: 9999px; text-transform: uppercase; margin-bottom: 14px;">
                CONNECTION VERIFIED
              </div>
              <h2 style="margin: 0 0 10px 0; font-size: 20px; color: #f8fafc;">
                Notification Pipeline is Online!
              </h2>
              <p style="margin: 0 0 18px 0; font-size: 14px; color: #94a3b8; line-height: 1.6;">
                Your Gmail SMTP configuration is properly authenticated and communicating with SmartShelf Vision AI.
                When products on your shelves drop to or below their threshold, low-stock warnings will be delivered to this address automatically.
              </p>
              <div style="background-color: #0f172a; border-radius: 8px; border: 1px solid #334155; padding: 14px 18px; font-size: 13px;">
                <div style="color: #64748b; margin-bottom: 4px;">Registered Recipient: <span style="color: #f1f5f9; font-weight: 600;">{clean_recipient}</span></div>
                <div style="color: #64748b;">Test Timestamp: <span style="color: #f1f5f9;">{now_str}</span></div>
              </div>
            </td>
          </tr>
          <tr>
            <td style="background-color: #0b1120; padding: 18px 30px; text-align: center; border-top: 1px solid #334155;">
              <p style="margin: 0; font-size: 11px; color: #64748b;">
                SmartShelf Vision AI System &bull; Test Notification Service
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    text_content = f"""[SMARTSHELF VISION AI - TEST NOTIFICATION]
Status: CONNECTION VERIFIED
Recipient: {recipient}
Timestamp: {now_str}

Your Gmail SMTP configuration is successfully configured!
You will automatically receive alerts when inventory drops below configured thresholds.
"""
    return subject, html_content, text_content
