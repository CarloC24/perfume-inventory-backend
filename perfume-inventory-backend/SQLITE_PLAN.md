# Plan: add a SQLite database and query it from endpoints

This document walks through adding a SQLite database to the FastAPI project and
exposing it through CRUD endpoints. Every code block is a complete file you can
copy as-is. The code was run end to end (server, curl, and a pytest suite)
before this was written.

## Approach

**Use SQLModel.** It is written by FastAPI's author and combines SQLAlchemy (the
database layer) with Pydantic (the validation layer). One class gives you both a
table and a request/response schema, which keeps the code small.

The alternative is plain SQLAlchemy 2.0 with separate Pydantic schemas. It is
more flexible but roughly doubles the boilerplate, so it is not the right
starting point.

## Target layout

All paths are relative to this folder (the one containing `main.py`).

```
main.py                 app, startup hook, router registration
database.py             engine, table creation, session dependency
models.py               Perfume table plus Create/Read/Update schemas
routers/__init__.py     empty, makes routers a package
routers/perfumes.py     the CRUD endpoints
tests/test_perfumes.py  pytest suite using an in-memory database
perfume.db              created at runtime, git-ignored
```

## Endpoints you will end up with

| Method and path             | Behavior                                                  |
| --------------------------- | --------------------------------------------------------- |
| `POST /perfumes`            | Validate body, insert, return 201 with the new record     |
| `GET /perfumes`             | List with optional `brand`, `q` name search, `offset`, `limit` |
| `GET /perfumes/low-stock`   | Rows where `quantity` is below a `threshold` query param  |
| `GET /perfumes/{id}`        | One row, or 404                                           |
| `PATCH /perfumes/{id}`      | Partial update using only the fields the client sent      |
| `DELETE /perfumes/{id}`     | Remove the row, return 204                                |

---

## Step 1. Install dependencies and configure the project

```bash
uv add sqlmodel
uv add --dev pytest httpx2
```

`httpx2` is what FastAPI's test client uses to make fake HTTP requests. Older
tutorials say `httpx`; the current starlette release prefers `httpx2`.

Add this line to the `.gitignore` at the repository root so the database file
never gets committed:

```
*.db
```

Append this to `pyproject.toml`. The `pythonpath` entry puts the project root
on Python's import path so tests can `from main import app`:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

---

## Step 2. The database connection

Three things live here: the engine (the connection to the file), a function
that creates tables, and a dependency that hands each request its own session.

#### `database.py`

```python
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///perfume.db"

# check_same_thread=False is SQLite-specific. FastAPI may serve a request on a
# different thread than the one that opened the connection, and SQLite refuses
# that by default.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    """Create every table that has been imported so far. Safe to call repeatedly."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency: one database session per request, closed afterwards."""
    with Session(engine) as session:
        yield session
```

**How `get_session` works.** It is a generator. FastAPI runs it up to the
`yield`, passes the session into your endpoint, and after the response is sent
it resumes the generator so the `with` block closes the session. You never open
or close sessions by hand in an endpoint.

**Why `create_all` needs the models imported first.** It only knows about
tables whose classes have been imported. In `main.py` the router import pulls
in `models.py`, so the order works out.

---

## Step 3. The models

One base class holds the shared fields. Four thin subclasses give you the
table and the three schemas.

#### `models.py`

```python
import enum

from sqlmodel import Field, SQLModel


class Gender(str, enum.Enum):
    """The only three values the gender column accepts."""

    masculine = "masculine"
    feminine = "feminine"
    unisex = "unisex"


class PerfumeBase(SQLModel):
    """Fields shared by the table and the request/response schemas."""

    name: str = Field(index=True)
    brand: str = Field(index=True)
    size_ml: int = Field(gt=0)
    quantity: int = Field(default=0, ge=0)
    price: float = Field(ge=0)
    gender: Gender = Field(default=Gender.unisex, index=True)


class Perfume(PerfumeBase, table=True):
    """The actual database table."""

    id: int | None = Field(default=None, primary_key=True)


class PerfumeCreate(PerfumeBase):
    """What POST /perfumes accepts. No id: the database assigns it."""


class PerfumeRead(PerfumeBase):
    """What every endpoint returns. id is always present here."""

    id: int


class PerfumeUpdate(SQLModel):
    """What PATCH accepts. Every field optional so clients send only what changed."""

    name: str | None = None
    brand: str | None = None
    size_ml: int | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, ge=0)
    gender: Gender | None = None
```

**Restricting a field to a fixed set of values.** `Gender` is a `str`-based
`Enum`, which is how you say "only these three". Because it subclasses `str`,
the value stores and serializes as plain text. FastAPI turns it into a dropdown
in the docs page and rejects anything else with a 422 whose message lists the
allowed values. Note this is enforced on `PerfumeCreate`, not on the table
class; see the gotchas at the end for a database-level guarantee.

**Why the split matters.** Returning the table class directly would leak any
internal column you add later. Accepting it on POST would let clients choose
their own IDs. Keeping `PerfumeUpdate` separate lets PATCH accept a body with
only one field.

**Validation is free, but only on the non-table classes.** `gt=0` and `ge=0`
are checked by Pydantic before your endpoint runs, so a negative `size_ml` gets
a 422 response automatically. This works because the endpoint accepts
`PerfumeCreate`, which is a plain schema. SQLModel skips validation entirely on
`table=True` classes, so `Perfume(size_ml=-5)` constructed directly in your own
code is accepted without complaint. Always take a Create/Update schema in the
endpoint signature and never the table class.

---

## Step 4. The endpoints

Every handler declares `session: Session = Depends(get_session)`. That is the
only way an endpoint reaches the database.

First create the empty package marker:

```bash
mkdir -p routers && touch routers/__init__.py
```

#### `routers/perfumes.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, col, select

from database import get_session
from models import Perfume, PerfumeCreate, PerfumeRead, PerfumeUpdate

router = APIRouter(prefix="/perfumes", tags=["perfumes"])


@router.post("", response_model=PerfumeRead, status_code=status.HTTP_201_CREATED)
def create_perfume(data: PerfumeCreate, session: Session = Depends(get_session)):
    perfume = Perfume.model_validate(data)
    session.add(perfume)
    session.commit()
    session.refresh(perfume)  # load the id the database just assigned
    return perfume


@router.get("", response_model=list[PerfumeRead])
def list_perfumes(
    brand: str | None = None,
    q: str | None = Query(default=None, description="Case-insensitive name search"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    statement = select(Perfume)
    if brand:
        statement = statement.where(Perfume.brand == brand)
    if q:
        statement = statement.where(col(Perfume.name).ilike(f"%{q}%"))
    statement = statement.order_by(col(Perfume.id)).offset(offset).limit(limit)
    return session.exec(statement).all()


# Declared BEFORE /{perfume_id}. Otherwise FastAPI tries to parse "low-stock"
# as an int and returns 422.
@router.get("/low-stock", response_model=list[PerfumeRead])
def list_low_stock(
    threshold: int = Query(default=5, ge=0),
    session: Session = Depends(get_session),
):
    statement = (
        select(Perfume)
        .where(Perfume.quantity < threshold)
        .order_by(col(Perfume.quantity))
    )
    return session.exec(statement).all()


@router.get("/{perfume_id}", response_model=PerfumeRead)
def get_perfume(perfume_id: int, session: Session = Depends(get_session)):
    perfume = session.get(Perfume, perfume_id)
    if perfume is None:
        raise HTTPException(status_code=404, detail="Perfume not found")
    return perfume


@router.patch("/{perfume_id}", response_model=PerfumeRead)
def update_perfume(
    perfume_id: int,
    data: PerfumeUpdate,
    session: Session = Depends(get_session),
):
    perfume = session.get(Perfume, perfume_id)
    if perfume is None:
        raise HTTPException(status_code=404, detail="Perfume not found")
    # exclude_unset: only touch fields the client actually sent, so an omitted
    # field is not overwritten with None.
    changes = data.model_dump(exclude_unset=True)
    perfume.sqlmodel_update(changes)
    session.add(perfume)
    session.commit()
    session.refresh(perfume)
    return perfume


@router.delete("/{perfume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_perfume(perfume_id: int, session: Session = Depends(get_session)):
    perfume = session.get(Perfume, perfume_id)
    if perfume is None:
        raise HTTPException(status_code=404, detail="Perfume not found")
    session.delete(perfume)
    session.commit()
```

**The pattern in every write endpoint** is `add`, `commit`, `refresh`. `add`
stages the object, `commit` writes it to disk, and `refresh` reloads it so
database-assigned values like `id` are populated before you return it.

**Reading.** `session.get(Model, id)` fetches one row by primary key.
`select(Model).where(...)` builds a query, and `session.exec(...)` runs it.
Chain `.offset()` and `.limit()` for pagination.

**Why `col()`.** `Perfume.name` is a plain `str` as far as a type checker
knows. Wrapping it in `col()` tells the checker it is a database column so
methods like `.ilike()` do not get flagged. The code runs without it, but
editors will complain.

**Why `""` instead of `"/"` for the collection routes.** The router already has
the prefix `/perfumes`. Using `"/"` would produce `/perfumes/` with a trailing
slash, and requests to `/perfumes` would redirect.

---

## Step 5. Wire it into the app

#### `main.py`

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import create_db_and_tables
from routers import perfumes  # importing the router also imports models.py


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts, before the first request.
    create_db_and_tables()
    yield
    # Anything after yield runs on shutdown.


app = FastAPI(title="Perfume Inventory", lifespan=lifespan)

app.include_router(perfumes.router)


@app.get("/hello")
def read_root():
    return {"message": "Hello World"}
```

**`lifespan`** replaces the older `@app.on_event("startup")` decorator, which
is deprecated. Code before `yield` runs at startup, code after runs at shutdown.

---

## Step 6. Tests

The tests never touch `perfume.db`. Each test gets a brand new in-memory
database, and the `get_session` dependency is swapped out so the app uses it.

#### `tests/test_perfumes.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from database import get_session
from main import app

SAUVAGE = {"name": "Sauvage", "brand": "Dior", "size_ml": 100, "quantity": 3, "price": 120.0}
BLEU = {"name": "Bleu de Chanel", "brand": "Chanel", "size_ml": 50, "quantity": 12, "price": 95.0}


@pytest.fixture(name="session")
def session_fixture():
    # A fresh in-memory database for every test. StaticPool keeps a single
    # connection alive so the in-memory DB is not thrown away between requests.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    # Swap the real get_session for one that hands back the test session.
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_create_perfume(client: TestClient):
    response = client.post("/perfumes", json=SAUVAGE)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["name"] == "Sauvage"


def test_create_rejects_bad_data(client: TestClient):
    response = client.post("/perfumes", json={**SAUVAGE, "size_ml": -5})
    assert response.status_code == 422


def test_get_missing_perfume_returns_404(client: TestClient):
    response = client.get("/perfumes/999")
    assert response.status_code == 404


def test_list_filters_by_brand(client: TestClient):
    client.post("/perfumes", json=SAUVAGE)
    client.post("/perfumes", json=BLEU)
    response = client.get("/perfumes", params={"brand": "Dior"})
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert names == ["Sauvage"]


def test_low_stock(client: TestClient):
    client.post("/perfumes", json=SAUVAGE)  # quantity 3
    client.post("/perfumes", json=BLEU)  # quantity 12
    response = client.get("/perfumes/low-stock", params={"threshold": 5})
    assert [p["name"] for p in response.json()] == ["Sauvage"]


def test_patch_only_changes_sent_fields(client: TestClient):
    created = client.post("/perfumes", json=SAUVAGE).json()
    response = client.patch(f"/perfumes/{created['id']}", json={"quantity": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["quantity"] == 10
    assert body["price"] == 120.0  # untouched


def test_delete_perfume(client: TestClient):
    created = client.post("/perfumes", json=SAUVAGE).json()
    response = client.delete(f"/perfumes/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/perfumes/{created['id']}").status_code == 404
```

Run them:

```bash
uv run pytest
```

Expected: `7 passed`. You may see a deprecation warning from anyio; it is
harmless.

**How the override works.** `app.dependency_overrides` is a dict mapping a
dependency function to a replacement. When an endpoint asks for `get_session`,
FastAPI calls the replacement instead. The tests use it to inject the in-memory
session. This is the standard way to test any FastAPI dependency.

---

## Step 7. Run it and verify by hand

Start the server from this folder (the database path is relative to the
working directory):

```bash
uv run fastapi dev main.py
```

On the first request `perfume.db` appears next to `main.py`. Open
http://127.0.0.1:8000/docs to use the interactive docs, or use curl.

Create two perfumes:

```bash
curl -X POST http://127.0.0.1:8000/perfumes \
  -H "Content-Type: application/json" \
  -d '{"name":"Sauvage","brand":"Dior","size_ml":100,"quantity":3,"price":120}'

curl -X POST http://127.0.0.1:8000/perfumes \
  -H "Content-Type: application/json" \
  -d '{"name":"Bleu de Chanel","brand":"Chanel","size_ml":50,"quantity":12,"price":95}'
```

Expected response for the first one:

```json
{"name":"Sauvage","brand":"Dior","size_ml":100,"quantity":3,"price":120.0,"id":1}
```

Filter and search:

```bash
curl "http://127.0.0.1:8000/perfumes?brand=Dior"
curl "http://127.0.0.1:8000/perfumes?q=bleu"
curl "http://127.0.0.1:8000/perfumes/low-stock?threshold=5"
```

Update only the quantity:

```bash
curl -X PATCH http://127.0.0.1:8000/perfumes/1 \
  -H "Content-Type: application/json" \
  -d '{"quantity":10}'
```

Expected: the same record with `"quantity":10` and every other field unchanged.

Delete and confirm it is gone:

```bash
curl -i -X DELETE http://127.0.0.1:8000/perfumes/1     # HTTP 204, empty body
curl http://127.0.0.1:8000/perfumes/1                  # {"detail":"Perfume not found"}
curl -i http://127.0.0.1:8000/perfumes/abc             # HTTP 422, "abc" is not an int
```

Look inside the database directly:

```bash
sqlite3 perfume.db "select id, name, brand, quantity from perfume;"
```

Finally check `git status`. You should see the new `.py` files but not
`perfume.db`.

---

## Step 8. Commit

```bash
git add -A
git status          # confirm perfume.db is not listed
git commit -m "Add SQLite database with perfume CRUD endpoints"
git push
```

---

## Things that will bite you if you do not know them

- **`create_all` only creates missing tables.** It will not add a column to a
  table that already exists. While the schema is still changing, delete
  `perfume.db` after editing `models.py` and let startup recreate it. Once you
  have real data, Alembic migrations replace that habit.
- **Route order matters.** `/perfumes/low-stock` must be declared before
  `/perfumes/{perfume_id}`. FastAPI matches routes top to bottom, and
  `{perfume_id}` would otherwise capture the word `low-stock`.
- **The database path is relative to where you start the server.** Run
  `fastapi dev` from the folder containing `main.py`, or use an absolute path
  in `DATABASE_URL`.
- **PATCH must use `exclude_unset=True`.** Without it, `model_dump()` returns
  every field including the ones the client did not send, and they all come
  back as `None`, wiping the record.
- **`table=True` models do not validate.** This is the biggest SQLModel
  surprise. Constraints like `gt=0` on the `Perfume` table class are recorded
  for the schema but never enforced when you build the object in Python. The
  API is still safe because request bodies are parsed as `PerfumeCreate`, which
  does validate. Scripts, seed data, and background jobs that build `Perfume`
  directly are not protected.
- **`Field(regex=...)` silently does nothing.** SQLModel accepts the argument
  and never applies it, and it has no `pattern=` argument at all. For string
  format rules, validate on the Create schema with a Pydantic field validator.
- **Enum values are checked by Pydantic, not by SQLite.** The generated column
  is a plain `VARCHAR`. A bad value still cannot reach it through the API, and
  SQLAlchemy raises a `LookupError` on commit if you build a table object
  directly, but raw SQL against the file is unchecked. To get a real database
  `CHECK` constraint, declare the column yourself:

  ```python
  from sqlalchemy import Column, Enum as SAEnum

  gender: Gender = Field(
      default=Gender.unisex,
      sa_column=Column(
          SAEnum(Gender, native_enum=False, create_constraint=True,
                 values_callable=lambda x: [i.value for i in x]),
          nullable=False, index=True,
      ),
  )
  ```

  That emits `CHECK (gender IN ('masculine', 'feminine', 'unisex'))` in the
  table definition. Adding it to an existing table needs a migration, since
  `create_all` will not alter a table that already exists.
- **SQLite allows one writer at a time.** Fine for a personal inventory or a
  small team. When that stops being true, changing `DATABASE_URL` to a Postgres
  URL moves you over with no endpoint changes.

## Out of scope for this pass

- **Migrations** with Alembic, once the schema stabilizes.
- **A stock-movement table** so every quantity change is recorded with a
  timestamp and reason, instead of overwriting `quantity` in place.
- **Authentication** before anything is exposed beyond localhost.
