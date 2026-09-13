"""Constants for the perfumes module."""

ROUTER_PREFIX = "/perfumes"
ROUTER_TAGS = ["perfumes"]

# gender is deliberately a free-form str, not an enum: the stored values are
# display strings like "For Men" / "For Women". An enum here would have to
# match those exactly, and a partial one silently makes PATCH stricter than
# POST.


class ErrorCode:
    PERFUME_NOT_FOUND = "Perfume not found"
    DUPLICATE_BARCODE = "A perfume with this barcode already exists"
