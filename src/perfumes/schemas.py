"""Pydantic models for the perfumes module: what the API accepts and returns."""

from sqlmodel import Field

from src.models import CustomModel
from src.perfumes.constants import Gender


class PerfumeBase(CustomModel):
    name: str = Field(index=True)
    brand: str = Field()
    type: str = Field()
    gender: str = Field()
    size: int = Field(default=0, ge=0)
    stock: int = Field(default=0, ge=0)
    price: float = Field(default=0.00, ge=0.00)
    location: str = Field(default="Backroom")
    # Unique: a barcode identifies one SKU, so it is the natural key POST
    # uses to decide between creating a row and updating the existing one.
    barcode: str = Field(unique=True, index=True)


class PerfumeCreate(PerfumeBase):
    """What POST /perfumes accepts. No id: the database assigns it."""


class PerfumeRead(PerfumeBase):
    id: int


class PerfumeUpdate(CustomModel):
    """What PATCH accepts. Every field optional so clients send only what changed."""

    name: str | None = None
    brand: str | None = None
    type: str | None = None
    gender: Gender | None = None
    size: int | None = None
    stock: int | None = None
    price: float | None = None
    location: str | None = None
    barcode: str | None = None
