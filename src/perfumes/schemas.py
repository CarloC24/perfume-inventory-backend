"""Pydantic models for the perfumes module: what the API accepts and returns."""

from pydantic import model_validator
from sqlmodel import Field

from src.models import CustomModel


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
    """What PATCH accepts. Every field optional so clients send only what changed.

    Types and constraints mirror PerfumeBase: anything PATCH accepts has to be
    something the row could have been created with in the first place. Letting
    the two drift means PATCH either waves through values POST rejects, or
    rejects values POST accepts.
    """

    name: str | None = None
    brand: str | None = None
    type: str | None = None
    gender: str | None = None
    size: int | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, ge=0.00)
    location: str | None = None
    barcode: str | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "PerfumeUpdate":
        """None here means "not sent", never "store a null".

        Every column behind these fields is NOT NULL, so an explicit null is a
        value the row cannot hold. Without this it reaches the database and
        comes back as a 500; omitting the field is how a client says "leave
        this alone".
        """
        nulled = sorted(
            field for field in self.model_fields_set if getattr(self, field) is None
        )
        if nulled:
            raise ValueError(
                "null is not an allowed value; omit a field to leave it "
                f"unchanged: {', '.join(nulled)}"
            )
        return self
