import logging
import secrets
import threading
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from . import crud
from .config import settings
from .database import Base, SessionLocal, engine
from .models import AdminUser
from .routes import admin, public, webhook
from .security import hash_password

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("diamond-raffle")

app = FastAPI(title="Diamond Raffle")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="raffle_admin_session",
    same_site="strict",
    max_age=8 * 3600,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(public.router)
app.include_router(webhook.router)
app.include_router(admin.router)


@app.exception_handler(HTTPException)
async def admin_auth_redirect(request: Request, exc: HTTPException):
    is_page_nav = request.method == "GET" and "text/html" in request.headers.get("accept", "")
    if exc.status_code == 401 and request.url.path.startswith("/admin") and is_page_nav:
        return RedirectResponse("/admin/login")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _bootstrap_admin(db) -> None:
    existing = db.execute(select(AdminUser)).scalars().first()
    if existing is not None:
        return
    email = settings.admin_email or "admin@apexcore.group"
    password = settings.admin_password or secrets.token_urlsafe(12)
    db.add(AdminUser(email=email, password_hash=hash_password(password)))
    db.commit()
    if not settings.admin_password:
        log.warning(
            "Kein ADMIN_PASSWORD gesetzt — generiertes Einmal-Passwort fuer %s: %s "
            "(bitte sofort ADMIN_PASSWORD env var setzen und Container neu starten)",
            email,
            password,
        )


def _cleanup_loop() -> None:
    while True:
        time.sleep(60)
        try:
            db = SessionLocal()
            try:
                crud.cleanup_expired_orders(db)
                raffle = crud.get_raffle(db)
                crud.refresh_raffle_status(db, raffle)
            finally:
                db.close()
        except Exception:
            log.exception("Cleanup-Loop Fehler")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        crud.ensure_seed_data(db)
        _bootstrap_admin(db)
    finally:
        db.close()
    threading.Thread(target=_cleanup_loop, daemon=True).start()
    log.info("Diamond Raffle gestartet — %s Lose, %s Tage Laufzeit", settings.raffle_total_tickets, settings.raffle_duration_days)


@app.get("/health")
def health():
    return {"status": "ok", "service": "diamond-raffle"}
