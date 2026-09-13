"""Database access for the perfumes module.

The router stays thin: it maps HTTP to these calls and back. Everything that
touches the session lives here.
"""

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.pagination import PaginationParams, paginate
from src.perfumes.models import Perfume
from src.perfumes.schemas import PerfumeCreate, PerfumeUpdate
from src.perfumes.utils import changed_fields


def get_all(session: Session, pagination: PaginationParams) -> list[Perfume]:
    statement = paginate(select(Perfume), pagination)
    return list(session.exec(statement).all())


def get_by_id(session: Session, perfume_id: int) -> Perfume | None:
    return session.get(Perfume, perfume_id)


def upsert_by_barcode(
    session: Session, data: PerfumeCreate
) -> tuple[Perfume, bool]:
    """Create the perfume, or update the existing row with the same barcode.

    Returns the row and whether it was newly created, so the caller can answer
    201 or 200. The barcode is unique, which is what makes POST safe to retry:
    a repeat of the same request updates rather than duplicating.
    """
    statement = select(Perfume).where(Perfume.barcode == data.barcode)
    existing = session.exec(statement).first()

    if existing is None:
        perfume = Perfume.model_validate(data)
        session.add(perfume)
        try:
            session.commit()
        except IntegrityError:
            # Another writer inserted this barcode between the select and the
            # commit; fall through and update the row they created.
            session.rollback()
            existing = session.exec(statement).one()
        else:
            session.refresh(perfume)
            return perfume, True

    return update(session, existing, data), False


def update(
    session: Session, perfume: Perfume, data: PerfumeCreate | PerfumeUpdate
) -> Perfume:
    perfume.sqlmodel_update(changed_fields(data))
    session.add(perfume)
    session.commit()
    session.refresh(perfume)
    return perfume


def delete(session: Session, perfume: Perfume) -> None:
    session.delete(perfume)
    session.commit()
