from fastapi import APIRouter, Request
from sqlalchemy.orm import Session
from .. import crud
from ..config import settings
from ..database import SessionLocal
from ..stripe_client import construct_webhook_event

router = APIRouter()


@router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        return {"ok": True}

    event = construct_webhook_event(payload, sig_header)
    db = SessionLocal()

    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            order_id = session.get("metadata", {}).get("order_id")
            if order_id:
                crud.mark_order_paid(db, int(order_id), session["id"])
        elif event["type"] == "checkout.session.async_payment_succeeded":
            session = event["data"]["object"]
            order_id = session.get("metadata", {}).get("order_id")
            if order_id:
                crud.mark_order_paid(db, int(order_id), session["id"])
        elif event["type"] == "checkout.session.expired":
            session = event["data"]["object"]
            order_id = session.get("metadata", {}).get("order_id")
            if order_id:
                crud.mark_order_failed(db, int(order_id))
        elif event["type"] == "checkout.session.async_payment_failed":
            session = event["data"]["object"]
            order_id = session.get("metadata", {}).get("order_id")
            if order_id:
                crud.mark_order_failed(db, int(order_id))
    finally:
        db.close()

    return {"ok": True}
