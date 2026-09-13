"""Constants for the perfumes module."""

import enum

ROUTER_PREFIX = "/perfumes"
ROUTER_TAGS = ["perfumes"]


class Gender(str, enum.Enum):
    masculine = "masculine"
    feminine = "feminine"
    unisex = "unisex"


class ErrorCode:
    PERFUME_NOT_FOUND = "Perfume not found"
    DUPLICATE_BARCODE = "A perfume with this barcode already exists"
