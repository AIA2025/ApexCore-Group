import stripe
import time
from fastapi import HTTPException
from .config import settings
from .models import Order


def is_configured() -> bool:
    return bool(settings.stripe_secret_key)


def create_checkout_session(order: Order, buyer_email: str, price_cents: int, currency: str):
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Zahlungen sind derzeit nicht verfügbar (Stripe nicht konfiguriert)"
        )

    stripe.api_key = settings.stripe_secret_key
    success_url = f"{settings.base_url}/erfolg?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.base_url}/abgebrochen"

    try:
        return stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer_email=buyer_email,
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "unit_amount": price_cents,
                    "product_data": {
                        "name": "Diamant-Raffle Los",
                        "description": "1 Los — Teilnahme an der 1,5 Karat Diamant Verlosung"
                    }
                },
                "quantity": order.quantity,
            }],
            metadata={"order_id": str(order.id)},
            success_url=success_url,
            cancel_url=cancel_url,
            expires_at=int(time.time()) + settings.reservation_minutes * 60,
        )
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Stripe-Fehler: {exc.user_message or str(exc)}"
        ) from exc


def construct_webhook_event(payload: bytes, sig_header: str):
    stripe.api_key = settings.stripe_secret_key
    try:
        return stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
