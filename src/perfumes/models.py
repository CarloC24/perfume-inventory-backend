"""Database models for the perfumes module."""

from sqlmodel import Field

from src.perfumes.schemas import PerfumeBase


class Perfume(PerfumeBase, table=True):
    # INTEGER PRIMARY KEY is an alias for SQLite's rowid, so leaving this None on
    # insert makes the database assign the next value.
    id: int | None = Field(default=None, primary_key=True, index=True)
