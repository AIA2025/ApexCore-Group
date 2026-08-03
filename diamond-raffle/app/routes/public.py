from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .. import crud
from ..config import settings
from ..database import get_db
from ..models import Order, OrderStatus
from ..ratelimit import checkout_limiter, client_ip
from ..schemas import CheckoutRequest
from ..stripe_client import create_checkout_session, is_configured

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request, db: Session = Depends(get_db)):
    raffle = crud.get_raffle(db)
    crud.refresh_raffle_status(db, raffle)
    sold = crud.get_sold_count(db)
    reserved = crud.get_reserved_count(db)

    ends_ts = int(raffle.ends_at.timestamp() * 1000)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "raffle": raffle,
        "sold": sold,
        "reserved": reserved,
        "ends_at_ms": ends_ts,
        "stripe_pk": settings.stripe_publishable_key,
        "stripe_configured": is_configured(),
    })


@router.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@router.get("/impressum", response_class=HTMLResponse)
def impressum_page(request: Request):
    return templates.TemplateResponse("impressum.html", {
        "request": request,
        "organizer_name": settings.organizer_name,
        "organizer_address": settings.organizer_address,
        "organizer_email": settings.organizer_email,
    })


@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@router.get("/erfolg", response_class=HTMLResponse)
def success_page(request: Request, session_id: str = ""):
    return templates.TemplateResponse("success.html", {
        "request": request,
        "session_id": session_id,
    })


@router.get("/abgebrochen", response_class=HTMLResponse)
def cancelled_page(request: Request):
    return templates.TemplateResponse("cancelled.html", {"request": request})


@router.get("/api/raffle")
def raffle_status(db: Session = Depends(get_db)):
    raffle = crud.get_raffle(db)
    crud.refresh_raffle_status(db, raffle)
    sold = crud.get_sold_count(db)
    reserved = crud.get_reserved_count(db)
    available = crud.get_available_count(db)

    now = datetime.utcnow()
    countdown = max(0, int((raffle.ends_at - now).total_seconds()))

    return {
        "status": raffle.status.value,
        "sold": sold,
        "reserved": reserved,
        "available": available,
        "total": raffle.total_tickets,
        "ends_at": raffle.ends_at.isoformat(),
        "countdown_seconds": countdown,
    }


@router.post("/api/checkout")
def start_checkout(payload: CheckoutRequest, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    if not checkout_limiter.is_allowed(ip):
        return {"error": "Zu viele Anfragen — bitte warten"}, 429

    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail="Zahlungen sind derzeit nicht verfügbar (Stripe nicht konfiguriert)"
        )

    order, buyer, ticket_numbers = crud.reserve_tickets_and_create_order(db, payload)
    session = create_checkout_session(
        order,
        buyer.email,
        order.amount_total_cents,
        settings.raffle_currency
    )
    order.stripe_session_id = session.id
    db.commit()

    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "order_id": order.id,
    }


@router.get("/api/orders/{session_id}")
def get_order_status(session_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.stripe_session_id == session_id).first()
    if not order:
        return {"status": "not_found"}

    return {
        "id": order.id,
        "status": order.status.value,
        "quantity": order.quantity,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "tickets": sorted([t.ticket_number for t in order.tickets]),
    }
