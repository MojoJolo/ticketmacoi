import asyncio
import re
import secrets
import shutil
import string
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import asyncpg
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, StringConstraints


BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR / "migrations"
STATIC_DIR = BASE_DIR / "static"
POSTERS_DIR = STATIC_DIR / "posters"
DATABASE_URL = "postgresql://postgres:postgres@db:5432/ticketmacoi"
BOOKING_REFERENCE_ALPHABET = string.ascii_uppercase + string.digits
VALID_EVENT_STATUSES = {"draft", "published", "cancelled"}
MANILA_TZ = timezone(timedelta(hours=8))


def seed_datetime(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=MANILA_TZ)

SEEDED_EVENTS = [
    {
        "title": "Kate Liu in Recital",
        "slug": "kate-liu-in-recital",
        "description": (
            "Rising to international acclaim after winning Third Prize at the 17th "
            "International Fryderyk Chopin Competition in Warsaw, Kate Liu also "
            "received the Best Mazurka Prize and the Audience Favorite Prize through "
            "the Polish National Radio. Since then, she has toured extensively, "
            "performing at world-renowned venues including the Seoul Arts Center, "
            "Tokyo Metropolitan Theatre, Warsaw National Philharmonic, La Maison "
            "Symphonique de Montreal, Carnegie Hall's Weill Recital Hall, Severance "
            "Hall, and the Kennedy Center. Kate Liu has collaborated with esteemed "
            "orchestras such as the Warsaw Philharmonic, Orchestre Symphonique de "
            "Montreal, Cleveland Orchestra, and Yomiuri Nippon Symphony Orchestra."
        ),
        "event_date": seed_datetime(2026, 5, 2, 19, 0),
        "venue_name": "Ayala Museum",
        "venue_address": "Makati City, Metro Manila",
        "poster_url": "https://www.veniccio.com/cdn/shop/files/Li_40.png?v=1773199640&width=1920",
        "status": "published",
        "producer_name": "Veniccio",
        "ticket_types": [
            {"name": "Rear Right Section", "price": Decimal("2500.00"), "total_slots": 48},
            {"name": "Stage Left", "price": Decimal("4500.00"), "total_slots": 24},
            {"name": "Premium Section", "price": Decimal("6000.00"), "total_slots": 64},
            {"name": "Patron", "price": Decimal("10000.00"), "total_slots": 16},
        ],
    },
    {
        "title": "Michael Valenciano in Recital",
        "slug": "michael-valenciano-in-recital",
        "description": (
            "The Manila Chamber Orchestra Foundation continues its 2026 Young Artists "
            "Series featuring pianist Michael Valenciano at Manila Pianos, Makati "
            "City. The event is made possible in cooperation with Manila Pianos, "
            "Double Pentagon Concerts, and Cultural Arts Events Organizer. Valenciano "
            "is widely regarded as one of the country's most promising young pianists "
            "today and is a two-time prizewinner at the National Music Competitions "
            "for Young Artists."
        ),
        "event_date": seed_datetime(2026, 6, 6, 19, 0),
        "venue_name": "Manila Pianos",
        "venue_address": "Makati City, Metro Manila",
        "poster_url": "https://www.veniccio.com/cdn/shop/files/Li_25.png?v=1774887946&width=1920",
        "status": "published",
        "producer_name": "Manila Chamber Orchestra Foundation",
        "ticket_types": [
            {"name": "General Admission", "price": Decimal("1500.00"), "total_slots": 120},
        ],
    },
    {
        "title": "Aristo Sham in Recital",
        "slug": "aristo-sham-in-recital",
        "description": (
            "Fresh from his historic triumph at the 2025 Van Cliburn International "
            "Piano Competition, where he claimed both the Gold Medal and Audience "
            "Award, Aristo Sham has captivated the global classical music world. "
            "Critics have praised his clarity, elegance, technique, and risk-taking, "
            "while major orchestras and presenters continue to feature him in "
            "high-profile performances around the world."
        ),
        "event_date": seed_datetime(2026, 11, 21, 19, 0),
        "venue_name": "Ayala Museum",
        "venue_address": "Makati City, Metro Manila",
        "poster_url": "https://www.veniccio.com/cdn/shop/files/Untitled_8_c3a5434a-008e-478a-b72c-cd281005676c.png?v=1770260903&width=1920",
        "status": "published",
        "producer_name": "Cultural Arts Events Organizer",
        "ticket_types": [
            {"name": "Rear Right Section", "price": Decimal("2000.00"), "total_slots": 48},
            {"name": "Standard Section", "price": Decimal("3000.00"), "total_slots": 56},
            {"name": "Premium Section", "price": Decimal("5000.00"), "total_slots": 40},
            {"name": "Patron", "price": Decimal("10000.00"), "total_slots": 16},
        ],
    },
    {
        "title": "The Golden Age of Kundiman",
        "slug": "the-golden-age-of-kundiman",
        "description": (
            "A full-evening vocal celebration of Filipino art song, featuring new "
            "arrangements of beloved kundiman repertoire, guest soloists, and a "
            "chamber ensemble devoted to the great songwriters of the early 20th "
            "century."
        ),
        "event_date": seed_datetime(2026, 7, 18, 19, 30),
        "venue_name": "Samsung Performing Arts Theater",
        "venue_address": "Circuit Makati, Makati City, Metro Manila",
        "poster_url": "/static/posters/tanghalang-gala.jpg",
        "status": "published",
        "producer_name": "Harana Arts Collective",
        "ticket_types": [
            {"name": "Balcony", "price": Decimal("1800.00"), "total_slots": 90},
            {"name": "Orchestra", "price": Decimal("2800.00"), "total_slots": 120},
            {"name": "Patron", "price": Decimal("4200.00"), "total_slots": 40},
        ],
    },
    {
        "title": "Strings Under The Stars",
        "slug": "strings-under-the-stars",
        "description": (
            "A warm outdoor-style concert featuring chamber orchestra favorites, "
            "serenades, and crossover arrangements presented in an intimate setting "
            "for first-time concertgoers and returning classical audiences alike."
        ),
        "event_date": seed_datetime(2026, 8, 8, 19, 0),
        "venue_name": "BGC Arts Center",
        "venue_address": "Bonifacio Global City, Taguig, Metro Manila",
        "poster_url": "/static/posters/philharmonic-evening.jpg",
        "status": "published",
        "producer_name": "Maestro Productions",
        "ticket_types": [
            {"name": "Lawn Circle", "price": Decimal("1500.00"), "total_slots": 150},
            {"name": "Preferred", "price": Decimal("2500.00"), "total_slots": 100},
            {"name": "VIP", "price": Decimal("3800.00"), "total_slots": 50},
        ],
    },
    {
        "title": "Cinematic Scores in Concert",
        "slug": "cinematic-scores-in-concert",
        "description": (
            "A symphonic night of film and television music, combining blockbuster "
            "themes, fantasy suites, and modern screen classics with synchronized "
            "lighting and live orchestral performance."
        ),
        "event_date": seed_datetime(2026, 9, 12, 20, 0),
        "venue_name": "New Frontier Theater",
        "venue_address": "Araneta City, Quezon City, Metro Manila",
        "poster_url": "/static/posters/manila-soundscape.jpg",
        "status": "published",
        "producer_name": "Screen Music Manila",
        "ticket_types": [
            {"name": "Upper Box", "price": Decimal("2200.00"), "total_slots": 160},
            {"name": "Lower Box", "price": Decimal("3200.00"), "total_slots": 100},
            {"name": "VIP", "price": Decimal("4800.00"), "total_slots": 50},
        ],
    },
    {
        "title": "Makati Jazz Assembly",
        "slug": "makati-jazz-assembly",
        "description": (
            "A curated city jazz night featuring big-band standards, modern fusion "
            "sets, and improvisation-heavy collaborations from Manila-based players "
            "and guest instrumentalists."
        ),
        "event_date": seed_datetime(2026, 10, 3, 19, 30),
        "venue_name": "Ayala Museum",
        "venue_address": "Makati City, Metro Manila",
        "poster_url": "/static/posters/manila-soundscape.jpg",
        "status": "published",
        "producer_name": "Blue Note Makati",
        "ticket_types": [
            {"name": "Regular", "price": Decimal("1700.00"), "total_slots": 120},
            {"name": "Preferred", "price": Decimal("2600.00"), "total_slots": 70},
            {"name": "Tableside", "price": Decimal("3900.00"), "total_slots": 32},
        ],
    },
    {
        "title": "Holiday Brass and Bells",
        "slug": "holiday-brass-and-bells",
        "description": (
            "A festive year-end concert with brass fanfares, seasonal choral works, "
            "and family-friendly holiday favorites performed by a combined brass "
            "ensemble and community chorus."
        ),
        "event_date": seed_datetime(2026, 12, 5, 19, 0),
        "venue_name": "The Theatre at Solaire",
        "venue_address": "Solaire Resort, Paranaque City, Metro Manila",
        "poster_url": "/static/posters/philharmonic-evening.jpg",
        "status": "published",
        "producer_name": "Yuletide Concerts PH",
        "ticket_types": [
            {"name": "Silver", "price": Decimal("2000.00"), "total_slots": 110},
            {"name": "Gold", "price": Decimal("3200.00"), "total_slots": 80},
            {"name": "Platinum", "price": Decimal("4600.00"), "total_slots": 36},
        ],
    },
]


class EventCreateRequest(BaseModel):
    title: Annotated[str, StringConstraints(min_length=1)]
    description: str | None = None
    event_date: datetime
    venue_name: Annotated[str, StringConstraints(min_length=1)]
    venue_address: str | None = None
    producer_name: str | None = None
    poster_url: str | None = None
    carousel_image_url: str | None = None
    card_image_url: str | None = None
    status: str = "draft"


class EventUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    event_date: datetime | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    producer_name: str | None = None
    poster_url: str | None = None
    carousel_image_url: str | None = None
    card_image_url: str | None = None
    status: str | None = None


class TicketTypeCreateRequest(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1)]
    price: Decimal = Field(gt=0)
    total_slots: int = Field(ge=0)


class TicketTypeUpdateRequest(BaseModel):
    name: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    total_slots: int | None = Field(default=None, ge=0)


class CreateOrderRequest(BaseModel):
    event_id: UUID
    ticket_type_id: UUID
    buyer_name: Annotated[str, StringConstraints(min_length=2)]
    buyer_email: EmailStr
    quantity: int = Field(ge=1, le=10)


def get_database_url() -> str:
    import os

    return os.getenv("DATABASE_URL", DATABASE_URL)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "event"


def serialize_record(record: asyncpg.Record | None) -> dict | None:
    if record is None:
        return None

    result = {}
    for key, value in dict(record).items():
        if isinstance(value, UUID):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
        else:
            result[key] = value
    return result


def validate_event_status(status: str | None) -> str | None:
    if status is None:
        return None

    if status not in VALID_EVENT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid event status.")

    return status


def clean_required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail=f"{field_name} is required.")
    return cleaned


async def run_migrations(pool: asyncpg.Pool) -> None:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    async with pool.acquire() as connection:
        await connection.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        for migration_file in migration_files:
            await connection.execute(migration_file.read_text())


async def generate_unique_slug(
    connection: asyncpg.Connection, title: str, exclude_event_id: UUID | None = None
) -> str:
    base_slug = slugify(title)
    candidate = base_slug
    suffix = 2

    while True:
        if exclude_event_id is None:
            existing = await connection.fetchval("SELECT id FROM events WHERE slug = $1;", candidate)
        else:
            existing = await connection.fetchval(
                "SELECT id FROM events WHERE slug = $1 AND id != $2;",
                candidate,
                exclude_event_id,
            )

        if existing is None:
            return candidate

        candidate = f"{base_slug}-{suffix}"
        suffix += 1


async def insert_ticket_types(
    connection: asyncpg.Connection, event_id: UUID, ticket_types: list[dict]
) -> None:
    for ticket_type in ticket_types:
        await connection.execute(
            """
            INSERT INTO ticket_types (
              event_id,
              name,
              price,
              total_slots
            )
            VALUES ($1, $2, $3, $4);
            """,
            event_id,
            ticket_type["name"],
            ticket_type["price"],
            ticket_type["total_slots"],
        )


async def seed_events(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as connection:
        async with connection.transaction():
            for event in SEEDED_EVENTS:
                existing_event = await connection.fetchrow(
                    "SELECT id FROM events WHERE slug = $1;",
                    event["slug"],
                )

                if existing_event is None:
                    existing_event = await connection.fetchrow(
                        """
                        INSERT INTO events (
                          title,
                          slug,
                          description,
                          event_date,
                          venue_name,
                          venue_address,
                          poster_url,
                          status,
                          producer_name
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        RETURNING id;
                        """,
                        event["title"],
                        event["slug"],
                        event["description"],
                        event["event_date"],
                        event["venue_name"],
                        event["venue_address"],
                        event["poster_url"],
                        event["status"],
                        event["producer_name"],
                    )

                existing_ticket_type_names = {
                    row["name"]
                    for row in await connection.fetch(
                        "SELECT name FROM ticket_types WHERE event_id = $1;",
                        existing_event["id"],
                    )
                }
                missing_ticket_types = [
                    ticket_type
                    for ticket_type in event["ticket_types"]
                    if ticket_type["name"] not in existing_ticket_type_names
                ]
                if missing_ticket_types:
                    await insert_ticket_types(connection, existing_event["id"], missing_ticket_types)


async def generate_booking_reference(connection: asyncpg.Connection) -> str:
    while True:
        suffix = "".join(secrets.choice(BOOKING_REFERENCE_ALPHABET) for _ in range(6))
        booking_reference = f"EVT-{suffix}"
        existing_reference = await connection.fetchval(
            "SELECT booking_reference FROM orders WHERE booking_reference = $1;",
            booking_reference,
        )
        if existing_reference is None:
            return booking_reference


async def create_pool_with_retry(retries: int = 10, delay: float = 2.0) -> asyncpg.Pool:
    last_error = None

    for _ in range(retries):
        try:
            return await asyncpg.create_pool(get_database_url())
        except Exception as error:
            last_error = error
            await asyncio.sleep(delay)

    raise last_error


async def fetch_ticket_types(connection: asyncpg.Connection, event_id: UUID) -> list[dict]:
    rows = await connection.fetch(
        """
        SELECT id, event_id, name, price, total_slots, created_at
        FROM ticket_types
        WHERE event_id = $1
        ORDER BY created_at ASC;
        """,
        event_id,
    )
    return [serialize_record(row) for row in rows]


async def fetch_event_with_ticket_types(connection: asyncpg.Connection, event_id: UUID) -> dict | None:
    event = await connection.fetchrow(
        """
        SELECT
          id,
          title,
          slug,
          description,
          event_date,
          venue_name,
          venue_address,
          poster_url,
          carousel_image_url,
          card_image_url,
          status,
          producer_name,
          created_at
        FROM events
        WHERE id = $1
          AND deleted_at IS NULL;
        """,
        event_id,
    )
    if event is None:
        return None

    serialized_event = serialize_record(event)
    serialized_event["ticket_types"] = await fetch_ticket_types(connection, event["id"])
    return serialized_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool_with_retry()
    app.state.pool = pool

    POSTERS_DIR.mkdir(parents=True, exist_ok=True)
    await run_migrations(pool)
    await seed_events(pool)

    yield

    await pool.close()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/events")
async def list_events(request: Request):
    async with request.app.state.pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
              e.id,
              e.title,
              e.slug,
              e.description,
              e.event_date,
              e.venue_name,
              e.venue_address,
              e.poster_url,
              e.carousel_image_url,
              e.card_image_url,
              e.status,
              e.producer_name,
              e.created_at,
              MIN(tt.price) AS ticket_price,
              COALESCE(SUM(tt.total_slots), 0) AS total_slots
            FROM events e
            LEFT JOIN ticket_types tt ON tt.event_id = e.id
            WHERE e.status = 'published'
              AND e.event_date > NOW()
              AND e.deleted_at IS NULL
            GROUP BY e.id
            ORDER BY e.event_date ASC;
            """
        )

    return [serialize_record(row) for row in rows]


@app.get("/api/events/{event_slug}")
async def get_event(event_slug: str, request: Request):
    async with request.app.state.pool.acquire() as connection:
        event = await connection.fetchrow(
            """
            SELECT
              id,
              title,
              slug,
              description,
              event_date,
              venue_name,
              venue_address,
              poster_url,
              carousel_image_url,
              card_image_url,
              status,
              producer_name,
              created_at
            FROM events
            WHERE slug = $1
              AND status = 'published'
              AND deleted_at IS NULL;
            """,
            event_slug,
        )

        if event is None:
            raise HTTPException(status_code=404, detail="Event not found.")

        response = serialize_record(event)
        response["ticket_types"] = await fetch_ticket_types(connection, event["id"])
        return response


@app.post("/api/orders")
@app.post("/api/admin/orders")
async def create_order(payload: CreateOrderRequest, request: Request):
    async with request.app.state.pool.acquire() as connection:
        async with connection.transaction():
            buyer_name = clean_required_text(payload.buyer_name, "Buyer name")
            event = await connection.fetchrow(
                """
                SELECT id, status
                FROM events
                WHERE id = $1
                  AND status = 'published';
                """,
                payload.event_id,
            )

            if event is None:
                raise HTTPException(status_code=404, detail="Event not found.")

            ticket_type = await connection.fetchrow(
                """
                SELECT id, event_id, name, price, total_slots
                FROM ticket_types
                WHERE id = $1
                  AND event_id = $2;
                """,
                payload.ticket_type_id,
                payload.event_id,
            )

            if ticket_type is None:
                raise HTTPException(status_code=422, detail="Invalid ticket type.")

            if ticket_type["total_slots"] < payload.quantity:
                raise HTTPException(status_code=422, detail="Not enough tickets available.")

            updated_ticket_type = await connection.fetchrow(
                """
                UPDATE ticket_types
                SET total_slots = total_slots - $2
                WHERE id = $1
                  AND total_slots >= $2
                RETURNING id, event_id, name, price, total_slots;
                """,
                ticket_type["id"],
                payload.quantity,
            )

            if updated_ticket_type is None:
                raise HTTPException(status_code=422, detail="Not enough tickets available.")

            booking_reference = await generate_booking_reference(connection)
            total_amount = updated_ticket_type["price"] * payload.quantity

            order = await connection.fetchrow(
                """
                INSERT INTO orders (
                  booking_reference,
                  event_id,
                  ticket_type_id,
                  buyer_name,
                  buyer_email,
                  quantity,
                  total_amount,
                  status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
                RETURNING
                  id,
                  booking_reference,
                  event_id,
                  ticket_type_id,
                  buyer_name,
                  buyer_email,
                  quantity,
                  total_amount,
                  status;
                """,
                booking_reference,
                event["id"],
                updated_ticket_type["id"],
                buyer_name,
                str(payload.buyer_email),
                payload.quantity,
                total_amount,
            )

            for ticket_number in range(1, payload.quantity + 1):
                await connection.execute(
                    """
                    INSERT INTO tickets (
                      order_id,
                      event_id,
                      ticket_number
                    )
                    VALUES ($1, $2, $3);
                    """,
                    order["id"],
                    event["id"],
                    ticket_number,
                )

    return {
        "booking_reference": order["booking_reference"],
        "event_id": str(order["event_id"]),
        "ticket_type_id": str(order["ticket_type_id"]),
        "buyer_name": order["buyer_name"],
        "buyer_email": order["buyer_email"],
        "quantity": order["quantity"],
        "total_amount": float(order["total_amount"]),
        "status": order["status"],
        "ticket_type_name": updated_ticket_type["name"],
    }


@app.get("/api/admin/events")
async def admin_list_events(request: Request):
    async with request.app.state.pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
              e.id,
              e.title,
              e.slug,
              e.description,
              e.event_date,
              e.venue_name,
              e.venue_address,
              e.poster_url,
              e.carousel_image_url,
              e.card_image_url,
              e.status,
              e.producer_name,
              e.created_at,
              COUNT(tt.id) AS ticket_type_count
            FROM events e
            LEFT JOIN ticket_types tt ON tt.event_id = e.id
            WHERE e.deleted_at IS NULL
            GROUP BY e.id
            ORDER BY e.created_at DESC;
            """
        )

    return [serialize_record(row) for row in rows]


@app.post("/api/admin/events")
async def admin_create_event(payload: EventCreateRequest, request: Request):
    validate_event_status(payload.status)

    async with request.app.state.pool.acquire() as connection:
        title = clean_required_text(payload.title, "Title")
        venue_name = clean_required_text(payload.venue_name, "Venue name")
        slug = await generate_unique_slug(connection, title)
        event = await connection.fetchrow(
            """
            INSERT INTO events (
              title,
              slug,
              description,
              event_date,
              venue_name,
              venue_address,
              poster_url,
              carousel_image_url,
              card_image_url,
              status,
              producer_name
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING
              id,
              title,
              slug,
              description,
              event_date,
              venue_name,
              venue_address,
              poster_url,
              carousel_image_url,
              card_image_url,
              status,
              producer_name,
              created_at;
            """,
            title,
            slug,
            payload.description,
            payload.event_date,
            venue_name,
            payload.venue_address,
            payload.poster_url,
            payload.carousel_image_url,
            payload.card_image_url,
            payload.status,
            payload.producer_name,
        )

    response = serialize_record(event)
    response["ticket_types"] = []
    return response


@app.get("/api/admin/events/{event_id}")
async def admin_get_event(event_id: UUID, request: Request):
    async with request.app.state.pool.acquire() as connection:
        event = await fetch_event_with_ticket_types(connection, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found.")
        return event


@app.patch("/api/admin/events/{event_id}")
async def admin_update_event(event_id: UUID, payload: EventUpdateRequest, request: Request):
    if payload.status is not None:
        validate_event_status(payload.status)

    async with request.app.state.pool.acquire() as connection:
        existing_event = await connection.fetchrow(
            "SELECT id, title FROM events WHERE id = $1 AND deleted_at IS NULL;",
            event_id,
        )
        if existing_event is None:
            raise HTTPException(status_code=404, detail="Event not found.")

        title = (
            clean_required_text(payload.title, "Title")
            if payload.title is not None
            else existing_event["title"]
        )
        slug = await generate_unique_slug(connection, title, exclude_event_id=event_id)
        venue_name = (
            clean_required_text(payload.venue_name, "Venue name")
            if payload.venue_name is not None
            else None
        )

        event = await connection.fetchrow(
            """
            UPDATE events
            SET
              title = COALESCE($2, title),
              slug = $3,
              description = COALESCE($4, description),
              event_date = COALESCE($5, event_date),
              venue_name = COALESCE($6, venue_name),
              venue_address = COALESCE($7, venue_address),
              poster_url = COALESCE($8, poster_url),
              carousel_image_url = COALESCE($9, carousel_image_url),
              card_image_url = COALESCE($10, card_image_url),
              status = COALESCE($11, status),
              producer_name = COALESCE($12, producer_name)
            WHERE id = $1
            RETURNING
              id,
              title,
              slug,
              description,
              event_date,
              venue_name,
              venue_address,
              poster_url,
              carousel_image_url,
              card_image_url,
              status,
              producer_name,
              created_at;
            """,
            event_id,
            title if payload.title is not None else None,
            slug,
            payload.description,
            payload.event_date,
            venue_name,
            payload.venue_address,
            payload.poster_url,
            payload.carousel_image_url,
            payload.card_image_url,
            payload.status,
            payload.producer_name,
        )

        response = serialize_record(event)
        response["ticket_types"] = await fetch_ticket_types(connection, event_id)
        return response


@app.delete("/api/admin/events/{event_id}")
async def admin_delete_event(event_id: UUID, request: Request):
    async with request.app.state.pool.acquire() as connection:
        result = await connection.execute(
            "UPDATE events SET deleted_at = NOW() WHERE id = $1 AND deleted_at IS NULL;",
            event_id,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Event not found.")
    return {"success": True}


@app.post("/api/admin/events/{event_id}/ticket-types")
async def admin_create_ticket_type(
    event_id: UUID, payload: TicketTypeCreateRequest, request: Request
):
    async with request.app.state.pool.acquire() as connection:
        event_exists = await connection.fetchval("SELECT id FROM events WHERE id = $1;", event_id)
        if event_exists is None:
            raise HTTPException(status_code=404, detail="Event not found.")

        ticket_type = await connection.fetchrow(
            """
            INSERT INTO ticket_types (
              event_id,
              name,
              price,
              total_slots
            )
            VALUES ($1, $2, $3, $4)
            RETURNING id, event_id, name, price, total_slots, created_at;
            """,
            event_id,
            clean_required_text(payload.name, "Ticket type name"),
            payload.price,
            payload.total_slots,
        )
        return serialize_record(ticket_type)


@app.patch("/api/admin/ticket-types/{ticket_type_id}")
async def admin_update_ticket_type(
    ticket_type_id: UUID, payload: TicketTypeUpdateRequest, request: Request
):
    async with request.app.state.pool.acquire() as connection:
        ticket_type = await connection.fetchrow(
            """
            UPDATE ticket_types
            SET
              name = COALESCE($2, name),
              price = COALESCE($3, price),
              total_slots = COALESCE($4, total_slots)
            WHERE id = $1
            RETURNING id, event_id, name, price, total_slots, created_at;
            """,
            ticket_type_id,
            clean_required_text(payload.name, "Ticket type name")
            if payload.name is not None
            else None,
            payload.price,
            payload.total_slots,
        )
        if ticket_type is None:
            raise HTTPException(status_code=404, detail="Ticket type not found.")
        return serialize_record(ticket_type)


@app.delete("/api/admin/ticket-types/{ticket_type_id}")
async def admin_delete_ticket_type(ticket_type_id: UUID, request: Request):
    async with request.app.state.pool.acquire() as connection:
        deleted_id = await connection.fetchval(
            "DELETE FROM ticket_types WHERE id = $1 RETURNING id;",
            ticket_type_id,
        )
        if deleted_id is None:
            raise HTTPException(status_code=404, detail="Ticket type not found.")
    return {"success": True}


@app.post("/api/admin/events/{event_id}/upload-poster")
async def admin_upload_poster(event_id: UUID, request: Request, file: UploadFile = File(...)):
    async with request.app.state.pool.acquire() as connection:
        event = await connection.fetchrow(
            "SELECT id, slug FROM events WHERE id = $1;",
            event_id,
        )
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found.")

        extension = Path(file.filename or "").suffix.lower() or ".jpg"
        filename = f"{event['slug']}-{uuid4().hex}{extension}"
        target_path = POSTERS_DIR / filename

        with target_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        poster_url = f"/static/posters/{filename}"
        await connection.execute(
            "UPDATE events SET poster_url = $2 WHERE id = $1;",
            event_id,
            poster_url,
        )

    return {"poster_url": poster_url}


VALID_IMAGE_TYPES = {"carousel", "card", "poster"}


@app.post("/api/admin/events/{event_id}/upload-image")
async def admin_upload_image(
    event_id: UUID,
    request: Request,
    image_type: str = Query(...),
    file: UploadFile = File(...),
):
    if image_type not in VALID_IMAGE_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Invalid image_type. Must be 'carousel', 'card', or 'poster'.",
        )

    async with request.app.state.pool.acquire() as connection:
        event = await connection.fetchrow(
            "SELECT id, slug FROM events WHERE id = $1;",
            event_id,
        )
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found.")

        extension = Path(file.filename or "").suffix.lower() or ".jpg"
        filename = f"{event['slug']}-{image_type}-{uuid4().hex}{extension}"
        target_path = POSTERS_DIR / filename

        with target_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image_url = f"/static/posters/{filename}"

        if image_type == "carousel":
            await connection.execute(
                "UPDATE events SET carousel_image_url = $2 WHERE id = $1;",
                event_id,
                image_url,
            )
            return {"carousel_image_url": image_url}
        elif image_type == "card":
            await connection.execute(
                "UPDATE events SET card_image_url = $2 WHERE id = $1;",
                event_id,
                image_url,
            )
            return {"card_image_url": image_url}
        else:
            await connection.execute(
                "UPDATE events SET poster_url = $2 WHERE id = $1;",
                event_id,
                image_url,
            )
            return {"poster_url": image_url}
