"""Database connection and session handling."""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from src.config import settings

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)


def create_db_and_tables() -> None:
    """Create every table from the models, bypassing migrations.

    For tests and throwaway local databases only. Do not call this at startup:
    it leaves alembic_version unstamped, which breaks the next migration. Use
    `alembic upgrade head` for anything whose data outlives the process.
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
