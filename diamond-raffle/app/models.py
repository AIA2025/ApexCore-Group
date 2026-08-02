from datetime import datetime
from enum import Enum
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class RaffleStatus(str, Enum):
    active = "active"
    paused = "paused"
    ended = "ended"


class TicketStatus(str, Enum):
    available = "available"
    reserved = "reserved"
    sold = "sold"
    drawn = "drawn"


class OrderStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    expired = "expired"
    failed = "failed"


class Raffle(Base):
    __tablename__ = "raffle"
    id = Column(Integer, primary_key=True, default=1)
    total_tickets = Column(Integer, default=750)
    status = Column(SQLEnum(RaffleStatus), default=RaffleStatus.active)
    starts_at = Column(DateTime, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=False)
    winner_ticket_number = Column(Integer, nullable=True)
    winner_drawn_at = Column(DateTime, nullable=True)


class Buyer(Base):
    __tablename__ = "buyer"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    street = Column(String(255), nullable=False)
    postal_code = Column(String(20), nullable=False)
    city = Column(String(255), nullable=False)
    country = Column(String(2), nullable=False)
    orders = relationship("Order", back_populates="buyer")


class Order(Base):
    __tablename__ = "order"
    id = Column(Integer, primary_key=True)
    buyer_id = Column(Integer, ForeignKey("buyer.id"), nullable=False)
    stripe_session_id = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.pending)
    quantity = Column(Integer, nullable=False)
    amount_total_cents = Column(Integer, nullable=False)
    reserved_until = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    buyer = relationship("Buyer", back_populates="orders")
    tickets = relationship("Ticket", back_populates="order")


class Ticket(Base):
    __tablename__ = "ticket"
    id = Column(Integer, primary_key=True)
    ticket_number = Column(Integer, unique=True, nullable=False, index=True)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.available)
    order_id = Column(Integer, ForeignKey("order.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    order = relationship("Order", back_populates="tickets")


class AdminUser(Base):
    __tablename__ = "admin_user"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
