import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src import database
from src.database import get_session
from src.main import app


@pytest.fixture(name="session")
def session_fixture(monkeypatch):
    # A fresh in-memory database per test, so nothing here can touch
    # perfume.db. StaticPool keeps one connection alive; without it each
    # checkout would get a new, empty in-memory database.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Overriding get_session is not enough on its own: the app's lifespan calls
    # create_db_and_tables() on the module-level engine, which would otherwise
    # open - and create - the configured database file during a test run.
    monkeypatch.setattr(database, "engine", engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        


@pytest.fixture(name="client")
def client_fixture(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="sauvage")
def sauvage_fixture():
    return {
        "name": "Dior Sauvage",
        "brand": "Dior",
        "type": "Eau de Toilette",
        "gender": "For Men",
        "size": 100,
        "stock": 20,
        "price": 74.50,
        "location": "Shelf A - Row 3",
        "barcode": "3348901250158",
    }


@pytest.fixture(name="libre")
def libre_fixture():
    return {
        "name": "YSL Libre",
        "brand": "YSL",
        "type": "Eau de Parfum",
        "gender": "For Women",
        "size": 90,
        "stock": 12,
        "price": 65.00,
        "location": "Shelf B - Row 2",
        "barcode": "3614272562481",
    }
