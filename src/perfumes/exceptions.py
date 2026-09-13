"""Exceptions raised by the perfumes module."""

from src.exceptions import Conflict, NotFound
from src.perfumes.constants import ErrorCode


class PerfumeNotFound(NotFound):
    DETAIL = ErrorCode.PERFUME_NOT_FOUND


class DuplicateBarcode(Conflict):
    DETAIL = ErrorCode.DUPLICATE_BARCODE
