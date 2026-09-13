"""Reusable dependencies for the perfumes module."""

from fastapi import Depends
from sqlmodel import Session

from src.database import get_session
from src.perfumes import service
from src.perfumes.exceptions import PerfumeNotFound
from src.perfumes.models import Perfume


def valid_perfume_id(
    perfume_id: int, session: Session = Depends(get_session)
) -> Perfume:
    """Resolve a path id to a row, or 404 before the handler runs."""
    perfume = service.get_by_id(session, perfume_id)
    if perfume is None:
        raise PerfumeNotFound()
    return perfume
