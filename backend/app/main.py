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
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, StringConstraints


BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR / "migrations"
STATIC_DIR = BASE_DIR / "static"
POSTERS_DIR = STATIC_DIR / "posters"
DATABASE_URL = "postgresql://postgres:postgres@db:5432/ticketmacoi"
BOOKING_REFERENCE_ALPHABET = string.ascii_uppercase + string.digits
VALID_EVENT_STATUSES = {"draft", "published", "cancelled"}

SEEDED_EVENTS = [
    {
        "title": "Manila Soundscape Live",
        "slug": "manila-soundscape-live",
        "description": (
            "An evening of contemporary Filipino pop and orchestral arrangements "
            "featuring guest vocalists and a full live band."
        ),
        "event_date": datetime.now(timezone.utc) + timedelta(days=21, hours=11),
        "venue_name": "New Frontier Theater",
        "venue_address": "Araneta City, Quezon City, Metro Manila",
        "poster_url": "http://localhost:4000/static/posters/manila-soundscape.jpg",
        "status": "published",
        "producer_name": "Harana Events PH",
        "ticket_types": [
            {"name": "General Admission", "price": Decimal("1850.00"), "total_slots": 180},
            {"name": "VIP", "price": Decimal("3200.00"), "total_slots": 60},
        ],
    },
    {
        "title": "Tanghalang Pilipino Gala Night",
        "slug": "tanghalang-pilipino-gala-night",
        "description": (
            "A formal theater showcase presenting a modern Filipino stage production "
            "with a post-show cast talk."
        ),
        "event_date": datetime.now(timezone.utc) + timedelta(days=35, hours=9),
        "venue_name": "Samsung Performing Arts Theater",
        "venue_address": "Circuit Makati, Makati City, Metro Manila",
        "poster_url": "http://localhost:4000/static/posters/tanghalang-gala.jpg",
        "status": "published",
        "producer_name": "Stagehouse Manila",
        "ticket_types": [
            {"name": "Balcony", "price": Decimal("1600.00"), "total_slots": 80},
            {"name": "Orchestra", "price": Decimal("2200.00"), "total_slots": 120},
        ],
    },
    {
        "title": "Philippine Philharmonic Evening",
        "slug": "philippine-philharmonic-evening",
        "description": (
            "A classical concert program of overtures, chamber works, and symphonic "
            "pieces led by resident guest conductors."
        ),
        "event_date": datetime.now(timezone.utc) + timedelta(days=49, hours=10),
        "venue_name": "The Theatre at Solaire",
        "venue_address": "Solaire Resort, Parañaque City, Metro Manila",
        "poster_url": "http://localhost:4000/static/posters/philharmonic-evening.jpg",
        "status": "published",
        "producer_name": "Maestro Productions",
        "ticket_types": [
            {"name": "Silver", "price": Decimal("2750.00"), "total_slots": 0},
            {"name": "Gold", "price": Decimal("4200.00"), "total_slots": 0},
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
    status: str = "draft"


class EventUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    event_date: datetime | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    producer_name: str | None = None
    poster_url: str | None = None
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
            events_count = await connection.fetchval("SELECT COUNT(*) FROM events;")

            if events_count == 0:
                for event in SEEDED_EVENTS:
                    created_event = await connection.fetchrow(
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
                    await insert_ticket_types(connection, created_event["id"], event["ticket_types"])
                return

            ticket_type_count = await connection.fetchval("SELECT COUNT(*) FROM ticket_types;")
            if ticket_type_count > 0:
                return

            for event in SEEDED_EVENTS:
                existing_event = await connection.fetchrow(
                    "SELECT id FROM events WHERE title = $1;",
                    event["title"],
                )
                if existing_event is not None:
                    await insert_ticket_types(connection, existing_event["id"], event["ticket_types"])


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
          status,
          producer_name,
          created_at
        FROM events
        WHERE id = $1;
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
              e.status,
              e.producer_name,
              e.created_at,
              MIN(tt.price) AS ticket_price,
              COALESCE(SUM(tt.total_slots), 0) AS total_slots
            FROM events e
            LEFT JOIN ticket_types tt ON tt.event_id = e.id
            WHERE e.status = 'published'
              AND e.event_date > NOW()
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
              status,
              producer_name,
              created_at
            FROM events
            WHERE slug = $1
              AND status = 'published';
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
              e.status,
              e.producer_name,
              e.created_at,
              COUNT(tt.id) AS ticket_type_count
            FROM events e
            LEFT JOIN ticket_types tt ON tt.event_id = e.id
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
              status,
              producer_name
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING
              id,
              title,
              slug,
              description,
              event_date,
              venue_name,
              venue_address,
              poster_url,
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
            "SELECT id, title FROM events WHERE id = $1;",
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
              status = COALESCE($9, status),
              producer_name = COALESCE($10, producer_name)
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
            payload.status,
            payload.producer_name,
        )

        response = serialize_record(event)
        response["ticket_types"] = await fetch_ticket_types(connection, event_id)
        return response


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

        poster_url = f"http://localhost:4000/static/posters/{filename}"
        await connection.execute(
            "UPDATE events SET poster_url = $2 WHERE id = $1;",
            event_id,
            poster_url,
        )

    return {"poster_url": poster_url}
