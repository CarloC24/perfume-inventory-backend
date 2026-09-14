"""Tests for src/database.py.

Every other test overrides get_session, so this is the one place the real
dependency and table creation are exercised. Both run against a patched
in-memory engine, never the configured database file.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from src import database
from src.perfumes.models import Perfume


@pytest.fixture(name="engine")
def engine_fixture(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(database, "engine", engine)
    return engine


def test_create_db_and_tables_creates_the_perfume_table(engine):
    database.create_db_and_tables()
    with Session(engine) as session:
        assert session.exec(select(Perfume)).all() == []


def test_create_db_and_tables_is_safe_to_repeat(engine):
    # It runs on every startup, so a second call must not fail on the tables
    # the first one created.
    database.create_db_and_tables()
    database.create_db_and_tables()


def test_get_session_yields_a_usable_session_and_then_finishes(engine):
    SQLModel.metadata.create_all(engine)
    sessions = database.get_session()

    session = next(sessions)
    assert isinstance(session, Session)
    assert session.get_bind() is engine

    session.add(
        Perfume(
            name="Probe",
            brand="B",
            type="Eau de Parfum",
            gender="For Men",
            size=50,
            stock=1,
            price=1.0,
            location="L",
            barcode="probe-1",
        )
    )
    session.commit()
    assert session.exec(select(Perfume)).one().name == "Probe"

    # Exhausting the generator leaves the `with` block that closes the session.
    with pytest.raises(StopIteration):
        next(sessions)
