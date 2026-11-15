# 05 — Database Design

## Multi-Agent Autonomous Researcher (MAAR)
### Phase 1: Application Foundation

---

## 1. Database Engine

| Property | Value |
|---|---|
| Engine | SQLite |
| Driver | aiosqlite (async) |
| ORM | SQLAlchemy 2.x (async declarative) |
| File location | Configurable via `DATABASE_URL` in `.env` |
| Default file path | `backend/maar_dev.db` |
| Initialization | Automatic `create_all()` on application startup |

SQLite is the correct choice for Phase 1 local development. It requires no server installation, initializes on first run, and is sufficient for single-user workloads. The schema is designed for forward-compatibility with PostgreSQL so migration requires only a connection string change.

---

## 2. Entity Relationship Diagram

Phase 1 contains a single entity. Future phases will add related tables.

```
┌────────────────────────────────────────────────────┐
│                 research_projects                  │
├──────────────────┬─────────────────────────────────┤
│ id               │ UUID (PK)                       │
│ title            │ VARCHAR(200) NOT NULL           │
│ research_question│ TEXT NOT NULL                   │
│ description      │ TEXT NULLABLE                   │
│ category         │ VARCHAR(100) NULLABLE           │
│ status           │ VARCHAR(20) NOT NULL            │
│ created_at       │ DATETIME NOT NULL               │
│ updated_at       │ DATETIME NOT NULL               │
└──────────────────┴─────────────────────────────────┘
```

Future phases will introduce related tables. Anticipated additions (not implemented in Phase 1):

```
research_projects
    │
    ├──< research_findings      (Phase 2)
    ├──< research_sources       (Phase 2)
    ├──< agent_tasks            (Phase 2)
    └──< agent_activity_logs    (Phase 2)
```

The `id` primary key on `research_projects` is a UUID so foreign keys in future tables reference stable, non-sequential identifiers.

---

## 3. Table: `research_projects`

### 3.1 Column Definitions

| Column | Type (SQLite) | Type (PostgreSQL) | Nullable | Constraints |
|---|---|---|---|---|
| `id` | TEXT | UUID | No | PRIMARY KEY, default: `uuid4()` |
| `title` | VARCHAR(200) | VARCHAR(200) | No | NOT NULL, CHECK len ≥ 1 |
| `research_question` | TEXT | TEXT | No | NOT NULL |
| `description` | TEXT | TEXT | Yes | — |
| `category` | VARCHAR(100) | VARCHAR(100) | Yes | — |
| `status` | VARCHAR(20) | VARCHAR(20) | No | NOT NULL, DEFAULT 'not_started' |
| `created_at` | DATETIME | TIMESTAMP WITH TIME ZONE | No | NOT NULL, DEFAULT utcnow |
| `updated_at` | DATETIME | TIMESTAMP WITH TIME ZONE | No | NOT NULL, DEFAULT utcnow |

### 3.2 Field Details

**`id`**
- Type: UUID stored as TEXT in SQLite; native UUID in PostgreSQL.
- Generated with `uuid.uuid4()` in Python before insert.
- Not auto-incremented. UUIDs are preferred for distributed identity, API exposure, and future sharding compatibility.
- Never exposed in URL path in a guessable sequence.

**`title`**
- Maximum 200 characters. Enforced by Pydantic at the API layer and by column length.
- Cannot be null or empty string. Whitespace is stripped before storage.
- No full-text index in Phase 1 (search is out of scope).

**`research_question`**
- TEXT column with no upper length enforcement at the database level; Pydantic enforces max 1000 characters.
- Required field.

**`description`**
- Optional free-text field.
- NULL if not provided.
- Pydantic enforces max 2000 characters if provided.

**`category`**
- Optional.
- Stored as a plain string in Phase 1. Category validation is enforced by the service layer against the defined list.
- Not a foreign key to a categories table — this avoids unnecessary complexity for a fixed, small list. If categories become user-defined in a later phase, migration to a foreign key is straightforward.

**`status`**
- Stored as a string value matching the `ProjectStatus` enum: `not_started`, `in_progress`, `completed`, `archived`.
- Default value: `not_started`.
- Validated by Pydantic enum on input.
- In PostgreSQL, this would use a native ENUM type or a CHECK constraint.

**`created_at`**
- Set once at INSERT time. Never updated.
- Stored as UTC. Python `datetime.utcnow()` or `datetime.now(timezone.utc)`.
- Serialized as ISO 8601 with `Z` suffix in API responses.

**`updated_at`**
- Set at INSERT and updated at every PATCH.
- In SQLAlchemy: `onupdate=func.now()` on the column definition.
- Stored as UTC.

### 3.3 SQLAlchemy ORM Model (Specification)

```python
# backend/app/models/project.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class ResearchProject(Base):
    __tablename__ = "research_projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    research_question: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_started"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
```

---

## 4. Indexes

| Index name | Table | Columns | Type | Reason |
|---|---|---|---|---|
| PRIMARY KEY | `research_projects` | `id` | Unique | Standard PK lookup |
| `ix_rp_status` | `research_projects` | `status` | Non-unique | Filtering by status on list/summary |
| `ix_rp_created_at` | `research_projects` | `created_at` | Non-unique | Ordering by date for recent projects |
| `ix_rp_category` | `research_projects` | `category` | Non-unique | Filtering by category (future) |

These indexes are defined in the SQLAlchemy model using `index=True` on the column definition. They are low-cost on a small dataset and prevent table scans when the project count grows.

---

## 5. Initialization Strategy

### Phase 1: `create_all()` on Startup

On application startup, `Base.metadata.create_all(bind=engine)` is called. This creates all tables that do not yet exist. It does not modify tables that already exist.

This approach is safe for Phase 1 where:
- There is a single developer.
- Schemas change frequently during development.
- Data loss from dropping and recreating the database is acceptable.

The startup code in `main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
```

### Phase 2+: Alembic Migrations

When the application reaches a state where schema changes must not destroy existing data (e.g., shared development environments, staging, production), Alembic will replace `create_all()`.

The migration path:

1. Add Alembic to `requirements.txt`.
2. Initialize: `alembic init alembic`.
3. Configure `alembic.ini` to use `DATABASE_URL` from the environment.
4. Generate the initial migration from the current models.
5. Replace `create_all()` startup logic with `alembic upgrade head`.

This transition requires no changes to the SQLAlchemy models themselves.

---

## 6. Migration Strategy (Phase 1 → PostgreSQL)

When switching from SQLite to PostgreSQL:

1. Change `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/maar
   ```
2. Change the async driver in `requirements.txt` from `aiosqlite` to `asyncpg`.
3. Install PostgreSQL locally or use a Docker container.
4. Run the application; `create_all()` creates the schema in PostgreSQL.

**No SQLAlchemy model changes are required** because:
- UUIDs are stored as TEXT in SQLite and can be mapped to PostgreSQL's UUID type by adding `from sqlalchemy.dialects.postgresql import UUID` in a separate PostgreSQL-specific model configuration (optional enhancement).
- `DATETIME` maps to PostgreSQL `TIMESTAMP`.
- All string and text column types are compatible.

For production, an Alembic migration script handles the initial schema creation on a fresh PostgreSQL database.

---

## 7. Data Integrity Rules

| Rule | Enforcement |
|---|---|
| `title` is never empty | Pydantic `min_length=1` + whitespace strip |
| `research_question` is never empty | Pydantic `min_length=1` |
| `status` is always a valid enum value | Pydantic enum validation |
| `id` is always a UUID | Python `uuid.uuid4()` at creation |
| `created_at` never changes after insert | Service layer: never passes `created_at` to UPDATE |
| `updated_at` reflects last modification | SQLAlchemy `onupdate` |
| `category` is null or a known value | Service layer validation against `VALID_CATEGORIES` |

---

## 8. Sample Data Strategy

Phase 1 does not seed the database with fake data. The empty state design in the frontend handles zero-project scenarios gracefully.

If a developer wants sample data for UI development, a standalone seed script can be added to `backend/scripts/seed_data.py`. It is never run automatically. Running it is an explicit developer action:

```
python scripts/seed_data.py
```

This script is optional and not part of the Phase 1 deliverable.
