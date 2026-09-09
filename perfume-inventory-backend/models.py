import enum
from sqlmodel import Field, SQLModel

class Gender(str, enum.Enum):
    masculine = "masculine"
    feminine = "feminine"
    unisex = "unisex"

class PerfumeBase(SQLModel): 
    name: str = Field(index=True)
    brand: str = Field()
    type: str = Field()
    gender: str = Field()
    size: int = Field(default=0, ge=0)
    stock: int = Field(default=0, ge=0)
    price: float = Field(default=0.00, ge=0.00)
    location: str = Field(default="Backroom")
    barcode: str = Field(nullable=False)

class Perfume(PerfumeBase, table=True):
    id: str = Field(primary_key=True, index=True)


class PerfumeCreate(PerfumeBase):
    """What POST /perfumes accepts. No id: the database assigns it."""


class PerfumeRead(PerfumeBase):
    id: str


class PerfumeUpdate(SQLModel):
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
