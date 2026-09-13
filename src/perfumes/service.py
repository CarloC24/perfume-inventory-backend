"""Database access for the perfumes module.

The router stays thin: it maps HTTP to these calls and back. Everything that
touches the session lives here.
"""

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.pagination import PaginationParams, paginate
from src.perfumes.exceptions import DuplicateBarcode
from src.perfumes.models import Perfume
from src.perfumes.schemas import PerfumeCreate, PerfumeUpdate
from src.perfumes.utils import changed_fields


def get_all(session: Session, pagination: PaginationParams) -> list[Perfume]:
    statement = paginate(select(Perfume), pagination)
    return list(session.exec(statement).all())


def get_by_id(session: Session, perfume_id: int) -> Perfume | None:
    return session.get(Perfume, perfume_id)


def get_by_barcode(session: Session, barcode: str) -> Perfume | None:
    statement = select(Perfume).where(Perfume.barcode == barcode)
    return session.exec(statement).first()


def upsert_by_barcode(
    session: Session, data: PerfumeCreate
) -> tuple[Perfume, bool]:
    """Create the perfume, or update the existing row with the same barcode.

    Returns the row and whether it was newly created, so the caller can answer
    201 or 200. The barcode is unique, which is what makes POST safe to retry:
    a repeat of the same request updates rather than duplicating.
    """
    existing = get_by_barcode(session, data.barcode)

    if existing is None:
        perfume = Perfume.model_validate(data)
        session.add(perfume)
        try:
            session.commit()
        except IntegrityError:
            # Another writer inserted this barcode between the select and the
            # commit; fall through and update the row they created.
            session.rollback()
            existing = get_by_barcode(session, data.barcode)
            if existing is None:
                raise  # something other than the barcode conflicted
        else:
            session.refresh(perfume)
            return perfume, True

    return update(session, existing, data), False


def update(
    session: Session, perfume: Perfume, data: PerfumeCreate | PerfumeUpdate
) -> Perfume:
    changes = changed_fields(data)
    perfume.sqlmodel_update(changes)
    session.add(perfume)
    try:
        session.commit()
    except IntegrityError:
        # Moving a row onto a barcode another row already holds is the client
        # naming an existing SKU, not a server fault: report it as a conflict
        # rather than letting the IntegrityError surface as a 500. Anything
        # else that violates a constraint is still a bug worth raising.
        session.rollback()
        barcode = changes.get("barcode")
        if barcode is not None and get_by_barcode(session, barcode) is not None:
            raise DuplicateBarcode() from None
        raise
    session.refresh(perfume)
    return perfume


def delete(session: Session, perfume: Perfume) -> None:
    session.delete(perfume)
    session.commit()
