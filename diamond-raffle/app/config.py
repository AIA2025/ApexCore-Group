import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://raffle:raffle@localhost:5432/raffle"
    base_url: str = "http://localhost:8000"
    session_secret: str = secrets.token_urlsafe(32)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    admin_email: str = ""
    admin_password: str = ""
    raffle_title: str = "1,5 Karat Diamant Raffle"
    diamond_carat: float = 1.5
    raffle_price_cents: int = 1000
    raffle_currency: str = "eur"
    raffle_total_tickets: int = 750
    raffle_duration_days: int = 30
    max_tickets_per_order: int = 20
    reservation_minutes: int = 30
    organizer_name: str = "[PLATZHALTER: Firmenname GmbH/d.o.o.]"
    organizer_address: str = "[PLATZHALTER: Straße, PLZ Ort, Land]"
    organizer_email: str = "[PLATZHALTER: kontakt@apexcore.group]"


settings = Settings()
