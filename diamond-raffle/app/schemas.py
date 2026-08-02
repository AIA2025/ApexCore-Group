from pydantic import BaseModel, EmailStr, Field


class CheckoutRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    street: str = Field(..., min_length=1, max_length=255)
    postal_code: str = Field(..., min_length=1, max_length=20)
    city: str = Field(..., min_length=1, max_length=255)
    country: str = Field(..., min_length=2, max_length=2)
    quantity: int = Field(..., ge=1, le=20)
    accept_terms: bool

    def __init__(self, **data):
        super().__init__(**data)
        if not self.accept_terms:
            raise ValueError("Terms must be accepted")
        if "country" in data:
            self.country = self.country.upper()


class RaffleStatusOut(BaseModel):
    status: str
    sold: int
    reserved: int
    available: int
    total: int
    ends_at: str
    countdown_seconds: int


class OrderStatusOut(BaseModel):
    id: int
    status: str
    quantity: int
    paid_at: str | None
    tickets: list[int]


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
