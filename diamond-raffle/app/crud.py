import secrets
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .models import AdminUser, Buyer, Order, OrderStatus, Raffle, RaffleStatus, Ticket, TicketStatus
from .schemas import CheckoutRequest
from .security import hash_password


def get_raffle(db: Session) -> Raffle:
    raffle = db.query(Raffle).first()
    if not raffle:
        raffle = Raffle(
            total_tickets=settings.raffle_total_tickets,
            ends_at=datetime.utcnow() + timedelta(days=settings.raffle_duration_days),
            status=RaffleStatus.active
        )
        db.add(raffle)
        db.commit()
        db.refresh(raffle)
    return raffle


def ensure_seed_data(db: Session) -> None:
    raffle = get_raffle(db)
    existing_count = db.query(Ticket).count()
    if existing_count < settings.raffle_total_tickets:
        for i in range(existing_count + 1, settings.raffle_total_tickets + 1):
            ticket = Ticket(ticket_number=i, status=TicketStatus.available)
            db.add(ticket)
        db.commit()


def cleanup_expired_orders(db: Session) -> None:
    now = datetime.utcnow()
    expired = db.query(Order).filter(
        Order.status == OrderStatus.pending,
        Order.reserved_until < now
    ).all()
    for order in expired:
        order.status = OrderStatus.expired
        for ticket in order.tickets:
            ticket.status = TicketStatus.available
            ticket.order_id = None
    if expired:
        db.commit()


def refresh_raffle_status(db: Session, raffle: Raffle) -> None:
    now = datetime.utcnow()
    if raffle.status == RaffleStatus.active and now > raffle.ends_at:
        raffle.status = RaffleStatus.ended
        db.commit()


def reserve_tickets_and_create_order(db: Session, payload: CheckoutRequest) -> tuple[Order, Buyer, list[int]]:
    cleanup_expired_orders(db)
    raffle = get_raffle(db)
    refresh_raffle_status(db, raffle)

    if raffle.status != RaffleStatus.active:
        raise HTTPException(status_code=409, detail="Die Verlosung ist nicht mehr aktiv")
    if payload.quantity > settings.max_tickets_per_order:
        raise HTTPException(status_code=400, detail=f"Maximal {settings.max_tickets_per_order} Lose pro Bestellung")

    locked_tickets = db.execute(
        select(Ticket)
        .where(Ticket.status == TicketStatus.available)
        .order_by(Ticket.ticket_number)
        .limit(payload.quantity)
        .with_for_update(skip_locked=True)
    ).scalars().all()

    if len(locked_tickets) < payload.quantity:
        db.rollback()
        raise HTTPException(status_code=409, detail="Nicht genug Lose verfügbar")

    buyer = db.query(Buyer).filter(Buyer.email == payload.email).first()
    if not buyer:
        buyer = Buyer(
            email=payload.email,
            full_name=payload.full_name,
            street=payload.street,
            postal_code=payload.postal_code,
            city=payload.city,
            country=payload.country
        )
        db.add(buyer)
        db.flush()

    order = Order(
        buyer_id=buyer.id,
        stripe_session_id=f"temp_{secrets.token_hex(16)}",
        status=OrderStatus.pending,
        quantity=payload.quantity,
        amount_total_cents=payload.quantity * settings.raffle_price_cents,
        reserved_until=datetime.utcnow() + timedelta(minutes=settings.reservation_minutes)
    )
    db.add(order)
    db.flush()

    ticket_numbers = []
    for ticket in locked_tickets:
        ticket.status = TicketStatus.reserved
        ticket.order_id = order.id
        ticket_numbers.append(ticket.ticket_number)

    db.commit()
    return order, buyer, ticket_numbers


def mark_order_paid(db: Session, order_id: int, stripe_session_id: str, timestamp: datetime = None) -> None:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.status = OrderStatus.paid
        order.stripe_session_id = stripe_session_id
        order.paid_at = timestamp or datetime.utcnow()
        for ticket in order.tickets:
            ticket.status = TicketStatus.sold
        db.commit()


def mark_order_failed(db: Session, order_id: int) -> None:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.status = OrderStatus.failed
        for ticket in order.tickets:
            ticket.status = TicketStatus.available
            ticket.order_id = None
        db.commit()


def draw_winner(db: Session) -> tuple[int, str, str]:
    raffle = get_raffle(db)
    raffle.status = RaffleStatus.ended

    sold_tickets = db.query(Ticket).filter(Ticket.status == TicketStatus.sold).all()
    if not sold_tickets:
        raise HTTPException(status_code=409, detail="Keine verkauften Lose vorhanden")

    winner_ticket = secrets.choice(sold_tickets)
    winner_ticket.status = TicketStatus.drawn
    raffle.winner_ticket_number = winner_ticket.ticket_number
    raffle.winner_drawn_at = datetime.utcnow()

    order = winner_ticket.order
    buyer = order.buyer

    db.commit()
    return winner_ticket.ticket_number, buyer.full_name, buyer.email


def get_sold_count(db: Session) -> int:
    return db.query(Ticket).filter(Ticket.status == TicketStatus.sold).count()


def get_reserved_count(db: Session) -> int:
    return db.query(Ticket).filter(Ticket.status == TicketStatus.reserved).count()


def get_available_count(db: Session) -> int:
    return db.query(Ticket).filter(Ticket.status == TicketStatus.available).count()


def get_revenue_cents(db: Session) -> int:
    total = db.query(Order).filter(Order.status == OrderStatus.paid).with_entities(
        db.func.sum(Order.amount_total_cents)
    ).scalar()
    return total or 0
