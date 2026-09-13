"""Global pagination module.

A shared dependency so every list endpoint takes the same query params and
applies them the same way, instead of each router inventing its own.
"""

from fastapi import Query
from sqlmodel.sql.expression import SelectOfScalar

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


class PaginationParams:
    """`limit`/`offset` query params, injected with `Depends()`."""

    def __init__(
        self,
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
        offset: int = Query(0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset


def paginate[T](
    statement: SelectOfScalar[T], pagination: PaginationParams
) -> SelectOfScalar[T]:
    """Apply `pagination` to `statement`."""
    return statement.offset(pagination.offset).limit(pagination.limit)
