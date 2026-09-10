"""Endpoint tests for /perfumes.

Each test gets a fresh in-memory database from the fixtures in conftest.py,
so ordering never matters and perfume.db is never touched.
"""

import pytest


# --------------------------------------------------------------------------
# GET /perfumes
# --------------------------------------------------------------------------


def test_list_is_empty_on_a_fresh_database(client):
    response = client.get("/perfumes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_created_rows(client, sauvage, libre):
    client.post("/perfumes", json=sauvage)
    client.post("/perfumes", json=libre)
    response = client.get("/perfumes")
    assert response.status_code == 200
    assert [p["name"] for p in response.json()] == ["Dior Sauvage", "YSL Libre"]


# --------------------------------------------------------------------------
# POST /perfumes
# --------------------------------------------------------------------------


def test_create_returns_201_and_an_assigned_id(client, sauvage):
    response = client.post("/perfumes", json=sauvage)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1  # the database assigned it; the client sent none
    assert body["name"] == "Dior Sauvage"


def test_ids_increment(client, sauvage, libre):
    first = client.post("/perfumes", json=sauvage).json()
    second = client.post("/perfumes", json=libre).json()
    assert [first["id"], second["id"]] == [1, 2]


def test_create_ignores_a_client_supplied_id(client, sauvage):
    # id is not on PerfumeCreate, so an id in the body is dropped rather than
    # honoured. Clients cannot choose their own primary keys.
    response = client.post("/perfumes", json={**sauvage, "id": 999})
    assert response.status_code == 201
    assert response.json()["id"] == 1


def test_response_exposes_exactly_the_read_schema(client, sauvage):
    body = client.post("/perfumes", json=sauvage).json()
    assert set(body) == set(sauvage) | {"id"}


def test_repeat_post_is_idempotent(client, sauvage):
    first = client.post("/perfumes", json=sauvage)
    assert first.status_code == 201

    again = client.post("/perfumes", json=sauvage)
    assert again.status_code == 200  # not 201: the row already existed
    assert again.json() == first.json()
    assert len(client.get("/perfumes").json()) == 1


def test_post_with_same_barcode_overwrites(client, sauvage):
    created = client.post("/perfumes", json=sauvage).json()
    response = client.post("/perfumes", json={**sauvage, "price": 99.0, "stock": 1})
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["price"] == 99.0
    assert response.json()["stock"] == 1
    assert len(client.get("/perfumes").json()) == 1


def test_post_leaves_omitted_fields_unchanged(client, sauvage):
    # The handler merges with exclude_unset=True, so a field the client leaves
    # out keeps its stored value instead of falling back to the PerfumeCreate
    # default. Only fields actually sent are written.
    created = client.post("/perfumes", json=sauvage).json()
    partial = {k: v for k, v in sauvage.items() if k not in {"stock", "location"}}
    response = client.post("/perfumes", json={**partial, "price": 55.0})
    assert response.status_code == 200
    assert response.json()["price"] == 55.0  # sent, so overwritten
    assert response.json()["stock"] == created["stock"]  # omitted, so kept
    assert response.json()["location"] == created["location"]


def test_different_barcode_creates_a_second_row(client, sauvage):
    client.post("/perfumes", json=sauvage)
    response = client.post("/perfumes", json={**sauvage, "barcode": "0000000000001"})
    assert response.status_code == 201
    assert len(client.get("/perfumes").json()) == 2


def test_create_rejects_negative_stock(client, sauvage):
    response = client.post("/perfumes", json={**sauvage, "stock": -5})
    assert response.status_code == 422


def test_create_rejects_negative_price(client, sauvage):
    response = client.post("/perfumes", json={**sauvage, "price": -1})
    assert response.status_code == 422


def test_create_rejects_a_missing_required_field(client, sauvage):
    response = client.post("/perfumes", json={k: v for k, v in sauvage.items() if k != "barcode"})
    assert response.status_code == 422


# --------------------------------------------------------------------------
# GET /perfumes/{id}
# --------------------------------------------------------------------------


def test_get_by_id_returns_the_row(client, sauvage):
    created = client.post("/perfumes", json=sauvage).json()
    response = client.get(f"/perfumes/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_by_id_404s_when_missing(client):
    response = client.get("/perfumes/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found"


def test_get_by_id_422s_on_a_non_integer_id(client):
    # The path param is typed int, so this never reaches the handler.
    assert client.get("/perfumes/abc").status_code == 422


# --------------------------------------------------------------------------
# PATCH /perfumes/{id}
# --------------------------------------------------------------------------


def test_patch_changes_only_the_fields_sent(client, sauvage):
    created = client.post("/perfumes", json=sauvage).json()
    response = client.patch(f"/perfumes/{created['id']}", json={"stock": 42})
    assert response.status_code == 200
    body = response.json()
    assert body["stock"] == 42
    assert body["price"] == created["price"]  # untouched
    assert body["name"] == created["name"]


def test_patch_with_an_empty_body_changes_nothing(client, sauvage):
    created = client.post("/perfumes", json=sauvage).json()
    response = client.patch(f"/perfumes/{created['id']}", json={})
    assert response.status_code == 200
    assert response.json() == created


def test_patch_404s_when_missing(client):
    response = client.patch("/perfumes/999", json={"stock": 1})
    assert response.status_code == 404


# --------------------------------------------------------------------------
# DELETE /perfumes/{id}
# --------------------------------------------------------------------------


def test_delete_removes_the_row(client, sauvage):
    created = client.post("/perfumes", json=sauvage).json()
    response = client.delete(f"/perfumes/{created['id']}")
    assert response.status_code == 204
    assert response.text == ""
    assert client.get(f"/perfumes/{created['id']}").status_code == 404
    assert client.get("/perfumes").json() == []


def test_delete_is_idempotent(client, sauvage):
    created = client.post("/perfumes", json=sauvage).json()
    assert client.delete(f"/perfumes/{created['id']}").status_code == 204
    # Same id again, and one that never existed: a missing row is not an error.
    assert client.delete(f"/perfumes/{created['id']}").status_code == 204
    assert client.delete("/perfumes/999").status_code == 204


# --------------------------------------------------------------------------
# Known PATCH bugs.
#
# These assert the behavior PATCH should have. They are xfail rather than
# deleted so the suite records the gap; each will start passing on its own
# once the underlying cause is fixed, and pytest reports XPASS to say so.
# --------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="PerfumeUpdate omits the ge=0 constraints that PerfumeBase declares, "
    "so the write is accepted and committed, and only then does PerfumeRead "
    "fail to serialize it -> 500 with a negative stock left in the database",
    strict=True,
)
def test_patch_rejects_negative_stock(client, sauvage):
    created = client.post("/perfumes", json=sauvage).json()
    response = client.patch(f"/perfumes/{created['id']}", json={"stock": -5})
    assert response.status_code == 422


@pytest.mark.xfail(
    reason="PATCH does not catch IntegrityError the way POST does, so moving a "
    "barcode onto one that already exists surfaces as a 500",
    strict=True,
)
def test_patch_to_a_duplicate_barcode_is_a_client_error(client, sauvage, libre):
    client.post("/perfumes", json=sauvage)
    second = client.post("/perfumes", json=libre).json()
    response = client.patch(
        f"/perfumes/{second['id']}", json={"barcode": sauvage["barcode"]}
    )
    assert response.status_code == 409


@pytest.mark.xfail(
    reason="PerfumeUpdate types gender as the Gender enum while PerfumeBase "
    "types it as str, so PATCH rejects the very values POST accepts and the "
    "seed data already uses",
    strict=True,
)
def test_patch_accepts_the_gender_values_post_accepts(client, sauvage):
    created = client.post("/perfumes", json=sauvage).json()
    response = client.patch(f"/perfumes/{created['id']}", json={"gender": "For Men"})
    assert response.status_code == 200
