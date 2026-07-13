"""
LionsylAI - Payment Integration
Stripe for international cards, SSLCommerz for Bangladesh
(bKash / Nagad / Rocket / local cards / bank transfer).
"""
from __future__ import annotations
import logging, hashlib, uuid
from datetime import datetime
from typing import Optional, Dict, Any

log = logging.getLogger("lionsylai.payment")

try:
    import stripe
    STRIPE_OK = True
except ImportError:
    STRIPE_OK = False

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

from config.settings import (
    STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY,
    STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID,
    SSLCOMMERZ_STORE_ID, SSLCOMMERZ_STORE_PASSWD,
    SSLCOMMERZ_API_URL, SSLCOMMERZ_VALIDATION_URL, SSLCOMMERZ_SANDBOX,
    APP_URL, PLANS, ENABLE_PAYMENTS,
)

if STRIPE_OK and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def stripe_configured() -> bool:
    return bool(STRIPE_OK and STRIPE_SECRET_KEY and STRIPE_PRICE_ID)


def sslcommerz_configured() -> bool:
    return bool(REQUESTS_OK and SSLCOMMERZ_STORE_ID and SSLCOMMERZ_STORE_PASSWD)


# ---- Stripe (international) ----------------------------------------

def create_checkout_session(
    user_email: str, user_id: int, billing: str = "month",
    success_path: str = "/?payment=success", cancel_path: str = "/?payment=cancel",
) -> Optional[str]:
    """Create a Stripe Checkout Session. Returns None if not configured (demo mode)."""
    if not ENABLE_PAYMENTS or not stripe_configured():
        log.warning("Stripe not configured - demo checkout")
        return None
    try:
        session = stripe.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=f"{APP_URL}{success_path}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}{cancel_path}",
            metadata={"user_id": str(user_id), "billing": billing},
            allow_promotion_codes=True,
            subscription_data={"metadata": {"user_id": str(user_id)}},
        )
        return session.url
    except Exception as e:
        log.error(f"Stripe checkout error: {e}")
        return None


def create_customer_portal(customer_id: str) -> Optional[str]:
    if not STRIPE_OK or not STRIPE_SECRET_KEY or not customer_id:
        return None
    try:
        session = stripe.billing_portal.Session.create(customer=customer_id, return_url=APP_URL)
        return session.url
    except Exception as e:
        log.error(f"Customer portal error: {e}")
        return None


def verify_subscription(stripe_sub_id: str) -> Dict[str, Any]:
    if not STRIPE_OK or not STRIPE_SECRET_KEY or not stripe_sub_id:
        return {"status": "unknown"}
    try:
        sub = stripe.Subscription.retrieve(stripe_sub_id)
        return {
            "status": sub["status"],
            "current_period_end": datetime.fromtimestamp(sub["current_period_end"]),
            "cancel_at_period_end": sub["cancel_at_period_end"],
        }
    except Exception as e:
        log.error(f"Subscription verify error: {e}")
        return {"status": "error"}


def handle_webhook(payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
    if not STRIPE_OK or not STRIPE_WEBHOOK_SECRET:
        return None
    try:
        return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        log.error(f"Webhook error: {e}")
        return None


# ---- SSLCommerz (Bangladesh: bKash / Nagad / Rocket / cards) -------

def create_sslcommerz_session(
    user_email: str, user_id: int, full_name: str,
    phone: str, amount_bdt: float, billing: str = "month",
) -> Optional[Dict[str, Any]]:
    """
    Initiate an SSLCommerz payment session.
    Returns {"gateway_url": ..., "transaction_id": ...} or None if unconfigured/failed.
    """
    if not ENABLE_PAYMENTS or not sslcommerz_configured():
        log.warning("SSLCommerz not configured - demo checkout")
        return None
    try:
        tran_id = f"LSAI-{user_id}-{uuid.uuid4().hex[:10]}"
        payload = {
            "store_id":       SSLCOMMERZ_STORE_ID,
            "store_passwd":   SSLCOMMERZ_STORE_PASSWD,
            "total_amount":   amount_bdt,
            "currency":       "BDT",
            "tran_id":        tran_id,
            "success_url":    f"{APP_URL}/?payment=success&gateway=sslcommerz&tran_id={tran_id}",
            "fail_url":       f"{APP_URL}/?payment=failed&gateway=sslcommerz",
            "cancel_url":     f"{APP_URL}/?payment=cancel&gateway=sslcommerz",
            "cus_name":       full_name or "LionsylAI Customer",
            "cus_email":      user_email,
            "cus_phone":      phone or "01700000000",
            "cus_add1":       "Dhaka",
            "cus_city":       "Dhaka",
            "cus_country":    "Bangladesh",
            "shipping_method":"NO",
            "product_name":   f"LionsylAI Professional ({billing})",
            "product_category": "SaaS Subscription",
            "product_profile": "general",
        }
        resp = requests.post(SSLCOMMERZ_API_URL, data=payload, timeout=15)
        data = resp.json()
        if data.get("status") == "SUCCESS" and data.get("GatewayPageURL"):
            return {"gateway_url": data["GatewayPageURL"], "transaction_id": tran_id}
        log.error(f"SSLCommerz init failed: {data}")
        return None
    except Exception as e:
        log.error(f"SSLCommerz session error: {e}")
        return None


def validate_sslcommerz_payment(val_id: str) -> bool:
    """Validate a completed SSLCommerz transaction server-side."""
    if not sslcommerz_configured() or not val_id:
        return False
    try:
        params = {
            "val_id": val_id,
            "store_id": SSLCOMMERZ_STORE_ID,
            "store_passwd": SSLCOMMERZ_STORE_PASSWD,
            "format": "json",
        }
        resp = requests.get(SSLCOMMERZ_VALIDATION_URL, params=params, timeout=15)
        data = resp.json()
        return data.get("status") in ("VALID", "VALIDATED")
    except Exception as e:
        log.error(f"SSLCommerz validation error: {e}")
        return False


# ---- UI helpers -----------------------------------------------------

def render_pricing_html(billing: str = "month", currency: str = "USD") -> str:
    plan = PLANS["pro"]
    if currency == "BDT":
        price  = plan["price_bdt_month"] if billing == "month" else plan["price_bdt_year"]
        period = "/mo" if billing == "month" else "/yr"
        symbol = "৳"
        save_note = "" if billing == "month" else (
            f'<div style="font-size:13px;color:#0AEFFF;margin-top:4px;">'
            f'Save {symbol}{plan["price_bdt_month"]*12 - plan["price_bdt_year"]:,}/yr vs monthly</div>'
        )
    else:
        price  = plan["price_month"] if billing == "month" else plan["price_year"]
        period = "/mo" if billing == "month" else "/yr"
        symbol = "$"
        save_note = "" if billing == "month" else (
            f'<div style="font-size:13px;color:#0AEFFF;margin-top:4px;">'
            f'Save ${plan["price_month"]*12 - plan["price_year"]}/yr vs monthly</div>'
        )
    features_html = "".join(
        f'<li style="padding:8px 0;border-bottom:1px solid #252836;color:#E0E4F0;">'
        f'&#10003; {f}</li>' for f in plan["features"]
    )
    return f"""
<div style="background:#141720;border:2px solid #6C63FF;border-radius:20px;
            padding:36px;max-width:420px;margin:0 auto;text-align:center;">
  <div style="font-size:14px;font-weight:700;color:#0AEFFF;letter-spacing:2px;
              text-transform:uppercase;margin-bottom:12px;">Professional Plan</div>
  <div style="font-size:52px;font-weight:900;color:#fff;line-height:1;">
    {symbol}{price:,}<span style="font-size:18px;color:#9CA3AF;">{period}</span>
  </div>
  {save_note}
  <ul style="list-style:none;padding:0;margin:24px 0;text-align:left;">
    {features_html}
  </ul>
  <div style="font-size:12px;color:#6B7280;margin-top:16px;">
    Cancel any time. No contracts. Billed securely.
  </div>
</div>
"""
