"""Service-level tests for src/perfumes/service.py.

These cover what the endpoints cannot reach. The router is not the only caller
of this module, so the guarantees it makes have to hold on their own.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.perfumes import service
from src.perfumes.exceptions import DuplicateBarcode
from src.perfumes.models import Perfume


def make_perfume(session, **overrides):
    perfume = Perfume(
        **{
            "name": "Probe",
            "brand": "B",
            "type": "Eau de Parfum",
            "gender": "For Men",
            "size": 50,
            "stock": 1,
            "price": 1.0,
            "location": "L",
            "barcode": "probe-1",
            **overrides,
        }
    )
    session.add(perfume)
    session.commit()
    session.refresh(perfume)
    return perfume


class NullsName:
    """A payload that sets name to null.

    PerfumeUpdate rejects this, so it cannot arrive over HTTP. It stands in for
    any future caller that reaches the service directly with a write the
    database will refuse for a reason other than the barcode.
    """

    def model_dump(self, **kwargs):
        return {"name": None}


def test_update_translates_a_barcode_conflict_into_a_client_error(session):
    taken = make_perfume(session, barcode="taken")
    mover = make_perfume(session, barcode="mover")

    class MovesOntoTakenBarcode:
        def model_dump(self, **kwargs):
            return {"barcode": taken.barcode}

    with pytest.raises(DuplicateBarcode):
        service.update(session, mover, MovesOntoTakenBarcode())

    session.rollback()
    assert service.get_by_barcode(session, "mover") is not None


def test_update_reraises_an_integrity_error_that_is_not_a_barcode_conflict(session):
    # A NOT NULL violation is a fault, not a conflict: it must surface as
    # itself rather than being reported as a duplicate barcode.
    perfume = make_perfume(session)
    with pytest.raises(IntegrityError):
        service.update(session, perfume, NullsName())


def test_get_by_barcode_finds_nothing_when_the_barcode_is_free(session):
    assert service.get_by_barcode(session, "no-such-barcode") is None
