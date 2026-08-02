# Diamond Raffle Website

1.5 Karat Diamond raffle with Stripe checkout integration, PostgreSQL buyer database, admin panel, and 30-day countdown.

## Local Development

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (if running without Docker)

### Setup

1. **Clone and configure**:
   ```bash
   cp .env.example .env
   ```

2. **Start services**:
   ```bash
   docker compose up --build
   ```

3. **Access**:
   - Landing page: http://localhost:8088
   - Admin panel: http://localhost:8088/admin (default: admin@apexcore.group)

### Environment Variables

See `.env.example` for all options. Key vars:
- `DATABASE_URL`: PostgreSQL connection
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`: Stripe API keys
- `ADMIN_PASSWORD`: Set to auto-generate a password on first startup (will be logged)
- `ORGANIZER_NAME`, `ORGANIZER_ADDRESS`, `ORGANIZER_EMAIL`: Legal information (must be filled before go-live)

### Stripe Setup (Local Testing)

1. **Get test keys** from https://dashboard.stripe.com/apikeys
2. **Set in `.env`**:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```
3. **Webhook secret** (for local testing with Stripe CLI):
   ```bash
   stripe listen --forward-to localhost:8088/api/stripe/webhook
   # Copy the whsec_... secret to .env STRIPE_WEBHOOK_SECRET
   ```

Without Stripe keys, the checkout flow shows a 503 error (graceful degradation).

## Production Deployment

### On VPS (76.13.138.73)

The deployment is pull-based via `cmd-api/poller.sh`. To enable deployment:

1. **Set up environment** on VPS:
   - Ensure Docker & Docker Compose are installed
   - Create `.env` in `/opt/openclaw/diamond-raffle/` with production secrets (Stripe live keys, secure `SESSION_SECRET`, etc.)
   - Update legal information (`ORGANIZER_*` vars)

2. **Add Caddy reverse-proxy snippet** (`/opt/openclaw/reverse-proxy/caddy/raffle.caddy`):
   ```
   raffle.apexcore.group {
     reverse_proxy localhost:8088
   }
   ```

3. **Reload Caddy**:
   ```bash
   docker exec caddy caddy reload
   ```

4. **Update the poller state** to track `main` branch (or whichever branch you push production code to):
   ```bash
   echo "main" > /opt/openclaw/poller-branch.txt
   ```

5. **Push to `main`** (or branch tracked by poller):
   ```bash
   git push origin main
   ```
   The poller will detect the push and trigger `cmd-api/server.py`'s `/deploy` endpoint to pull and restart the raffle service.

## Admin Panel

### Pages
- **Dashboard** (`/admin`): Overview of sales, reservations, revenue
- **Buyers** (`/admin/buyers`): Full buyer database with address info
- **Draw** (`/admin/draw`): Conduct the final winner draw (irreversible)
- **CSV Export** (`/admin/export.csv`): Download all buyer data

### Authentication
- Session-based (Starlette SessionMiddleware, bcrypt hashing)
- Auto-bootstrap on first startup with `ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars
- If `ADMIN_PASSWORD` not set, a one-time password is auto-generated and logged

## Database

PostgreSQL with SQLAlchemy 2.0 ORM:
- `Raffle`: Single raffle record with status, countdown, winner info
- `Buyer`: Email (unique), name, address
- `Order`: Links buyer to payment status, Stripe session, reserved tickets
- `Ticket`: Individual tickets with number (1–750), status (available/reserved/sold/drawn)
- `AdminUser`: Admin login credentials

Ticket reservation uses Postgres `FOR UPDATE SKIP LOCKED` to atomically prevent overselling under concurrent checkouts.

## Legal & Compliance

**⚠️ IMPORTANT**: Paid raffles (Verlosungen) in Germany and Austria require a gambling permit (Glücksspielerlaubnis) from the relevant authority before accepting real money. This template uses placeholder text (`[PLATZHALTER]`) for legal sections to avoid fabricating claims.

Before go-live, update:
1. **Terms of Service** (`/terms`): Legal right-to-cancel, data processing, dispute resolution
2. **Impressum** (`/impressum`): Operator name, address, tax ID, responsible person
3. **Datenschutz** (`/privacy`): GDPR compliance, data retention, email consent
4. **Diamond Certificate**: Add actual certificate number and images to the landing page

## Troubleshooting

### "Checkout session failed"
- Verify `STRIPE_SECRET_KEY` is set and valid
- Check Stripe webhook is configured to receive `checkout.session.completed` events

### "Nicht genug Lose verfügbar"
- All 750 tickets are sold or reserved; raffle is at capacity

### Admin password not working
- Check logs: `docker logs raffle-api | grep -i password`
- If `ADMIN_PASSWORD` not set, a generated password was logged at startup
- Reset by stopping the container, clearing the admin user from DB, and restarting

### Database connection refused
- Ensure `db` service is healthy: `docker compose ps`
- Check `DATABASE_URL` matches `db` hostname in docker-compose.yml

## Architecture

- **FastAPI** (Python): REST API + server-rendered Jinja2 templates
- **PostgreSQL**: Buyer, order, ticket data + row-level concurrency control
- **Stripe**: Payment processing with webhook integration
- **Caddy**: Reverse proxy (on VPS)
- **Docker**: Containerized deployment

## Files

```
diamond-raffle/
├── app/
│   ├── main.py                 # FastAPI app, startup seeding, cleanup loop
│   ├── config.py               # Settings (env vars)
│   ├── database.py             # SQLAlchemy engine/session
│   ├── models.py               # ORM models (Raffle, Buyer, Order, Ticket, AdminUser)
│   ├── schemas.py              # Pydantic schemas
│   ├── security.py             # Auth, password hashing
│   ├── ratelimit.py            # In-memory rate limiting
│   ├── stripe_client.py        # Stripe API wrapper
│   ├── crud.py                 # Business logic (ticket reservation, winner draw, cleanup)
│   ├── routes/
│   │   ├── public.py           # Landing, checkout, order status, legal pages
│   │   ├── webhook.py          # Stripe webhook handler
│   │   └── admin.py            # Admin login/dashboard/buyers/draw/export
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html          # Landing page
│   │   ├── success.html
│   │   ├── cancelled.html
│   │   ├── winner.html
│   │   ├── terms.html
│   │   ├── impressum.html
│   │   ├── privacy.html
│   │   └── admin/
│   │       ├── login.html
│   │       ├── dashboard.html
│   │       ├── buyers.html
│   │       └── draw.html
│   └── static/
│       ├── style.css           # Dark luxury theme
│       ├── countdown.js        # Live countdown + progress bar
│       └── checkout.js         # Stripe checkout integration
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md                   # This file
```

## Support

For issues or questions, open an issue in the ApexCore Group repository.
