"""Helpers for the perfumes module."""

from typing import Any

from sqlmodel import SQLModel


def changed_fields(data: SQLModel) -> dict[str, Any]:
    """Only the fields the client actually sent.

    Fields left out of the request keep their stored value rather than being
    overwritten with a schema default.
    """
    return data.model_dump(exclude_unset=True)
