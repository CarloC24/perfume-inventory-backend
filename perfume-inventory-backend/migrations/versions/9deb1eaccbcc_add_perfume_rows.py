"""add perfume rows

Revision ID: 9deb1eaccbcc
Revises: 462dbc8a7939
Create Date: 2026-09-08 23:36:53.676475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '9deb1eaccbcc'
down_revision: Union[str, Sequence[str], None] = '462dbc8a7939'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# A lightweight description of the table as it exists at THIS revision.
# Deliberately not importing the Perfume model: models change over time, but a
# migration must keep working against the schema that was current when it was
# written.
perfume_table = sa.table(
    "perfume",
    sa.column("id", sa.String),
    sa.column("name", sa.String),
    sa.column("brand", sa.String),
    sa.column("type", sa.String),
    sa.column("gender", sa.String),
    sa.column("size", sa.Integer),
    sa.column("stock", sa.Integer),
    sa.column("price", sa.Float),
    sa.column("location", sa.String),
    sa.column("barcode", sa.String),
)

# IDs are hard-coded rather than generated at runtime so that the migration is
# repeatable and downgrade() can delete exactly the rows upgrade() inserted.
SEED_ROWS = [
    {
        "id": "30c77537-4788-4c21-b5c1-5c7b38a7d399",
        "name": "Chanel Chance",
        "brand": "Chanel",
        "type": "Eau de Parfum",
        "gender": "For Women",
        "size": 100,
        "stock": 15,
        "price": 89.99,
        "location": "Shelf A - Row 2",
        "barcode": "3145891265478",
    },
    {
        "id": "000b8753-1e80-4aa0-a7ae-03b4a920d771",
        "name": "Dior Sauvage",
        "brand": "Dior",
        "type": "Eau de Toilette",
        "gender": "For Men",
        "size": 100,
        "stock": 20,
        "price": 74.50,
        "location": "Shelf A - Row 3",
        "barcode": "3348901250158",
    },
    {
        "id": "180407ab-e802-43d3-a29a-5ae34cb07e7b",
        "name": "Versace Dylan Blue",
        "brand": "Versace",
        "type": "Eau de Toilette",
        "gender": "For Men",
        "size": 100,
        "stock": 18,
        "price": 92.00,
        "location": "Shelf B - Row 1",
        "barcode": "8011003835521",
    },
    {
        "id": "dc541389-b895-48d9-a1f8-a20c6332fc41",
        "name": "YSL Libre",
        "brand": "YSL",
        "type": "Eau de Parfum",
        "gender": "For Women",
        "size": 90,
        "stock": 12,
        "price": 65.00,
        "location": "Shelf B - Row 2",
        "barcode": "3614272562481",
    },
    {
        "id": "5129cea9-39d4-4726-b6bb-995a72f79ef5",
        "name": "Bleu de Chanel",
        "brand": "Chanel",
        "type": "Eau de Parfum",
        "gender": "For Men",
        "size": 150,
        "stock": 8,
        "price": 120.00,
        "location": "Shelf A - Row 4",
        "barcode": "3145891267229",
    },
]


def upgrade() -> None:
    """Insert the initial perfume inventory."""
    op.bulk_insert(perfume_table, SEED_ROWS)


def downgrade() -> None:
    """Remove exactly the rows this migration inserted."""
    op.execute(
        perfume_table.delete().where(
            perfume_table.c.id.in_([row["id"] for row in SEED_ROWS])
        )
    )
