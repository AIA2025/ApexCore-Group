from datetime import datetime, timedelta
from io import StringIO
import csv
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .. import crud
from ..config import settings
from ..database import get_db
from ..models import AdminUser, Order, OrderStatus, Raffle, RaffleStatus
from ..ratelimit import client_ip, login_limiter
from ..schemas import AdminLoginRequest
from ..security import hash_password, require_admin, verify_password

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/api/admin/login")
async def admin_login(payload: AdminLoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    if not login_limiter.is_allowed(ip):
        raise HTTPException(status_code=429, detail="Zu viele Anfragen")

    admin = db.query(AdminUser).filter(AdminUser.email == payload.email).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")

    request.session["admin_id"] = admin.id
    return {"ok": True}


@router.post("/api/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    raffle = crud.get_raffle(db)
    crud.refresh_raffle_status(db, raffle)
    sold = crud.get_sold_count(db)
    reserved = crud.get_reserved_count(db)
    revenue_cents = crud.get_revenue_cents(db)
    recent_orders = db.query(Order).filter(
        Order.status == OrderStatus.paid
    ).order_by(Order.paid_at.desc()).limit(10).all()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "raffle": raffle,
        "sold": sold,
        "reserved": reserved,
        "revenue_cents": revenue_cents,
        "recent_orders": recent_orders,
    })


@router.get("/buyers", response_class=HTMLResponse)
async def buyers_page(request: Request, admin: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.status == OrderStatus.paid).order_by(Order.paid_at.desc()).all()
    return templates.TemplateResponse("admin/buyers.html", {
        "request": request,
        "orders": orders,
    })


@router.get("/draw", response_class=HTMLResponse)
async def draw_page(request: Request, admin: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    raffle = crud.get_raffle(db)
    crud.refresh_raffle_status(db, raffle)
    sold = crud.get_sold_count(db)
    return templates.TemplateResponse("admin/draw.html", {
        "request": request,
        "raffle": raffle,
        "sold": sold,
    })


@router.post("/api/admin/draw")
async def draw_winner_api(admin: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    raffle = crud.get_raffle(db)
    if raffle.winner_ticket_number:
        raise HTTPException(status_code=409, detail="Gewinner bereits gezogen")

    ticket_number, buyer_name, buyer_email = crud.draw_winner(db)
    return {
        "ticket_number": ticket_number,
        "buyer_name": buyer_name,
        "buyer_email": buyer_email,
    }


@router.post("/api/admin/extend-deadline")
async def extend_deadline(
    payload: dict,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    raffle = crud.get_raffle(db)
    days = payload.get("days", 1)
    raffle.ends_at = datetime.utcnow() + timedelta(days=days)
    if raffle.status == RaffleStatus.ended:
        raffle.status = RaffleStatus.active
    db.commit()
    return {"ok": True, "new_end_time": raffle.ends_at.isoformat()}


@router.get("/export.csv")
async def export_csv(admin: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.status == OrderStatus.paid).order_by(Order.paid_at.desc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Bezahlt am", "Name", "E-Mail", "Adresse", "Lose", "Losnummern", "Betrag"])

    for order in orders:
        buyer = order.buyer
        paid_at = order.paid_at.strftime("%d.%m.%Y %H:%M") if order.paid_at else "–"
        address = f"{buyer.street}, {buyer.postal_code} {buyer.city}, {buyer.country}"
        ticket_numbers = ",".join(str(t.ticket_number) for t in sorted(order.tickets, key=lambda x: x.ticket_number))
        amount = f"{order.amount_total_cents / 100:.2f}"

        writer.writerow([paid_at, buyer.full_name, buyer.email, address, order.quantity, ticket_numbers, amount])

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=buyers.csv"}
    )
