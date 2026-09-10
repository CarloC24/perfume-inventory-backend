# Manual API tests

Plain `curl` commands for every `/perfumes` endpoint. Each one is
self-contained: copy a single block and run it, or paste it into Postman via
**Import → Raw text**.

Start the server first:

```bash
uv run fastapi dev main.py
```

Everything below assumes `http://localhost:8000`. If you run on another port,
replace the host in each command.

Steps 6 onward use id `6`, which is what step 2 creates on a freshly seeded
database. If your POST returns a different id, use that instead.

---

## 1. List everything

Expect `200` and the seeded inventory.

```bash
curl http://localhost:8000/perfumes
```

## 2. Create a perfume

Expect `201` and a database-assigned `id`.

```bash
curl -X POST http://localhost:8000/perfumes \
  -H "Content-Type: application/json" \
  -d '{"name": "Curl Test Scent", "brand": "ACME", "type": "Eau de Parfum", "gender": "unisex", "size": 50, "stock": 3, "price": 42.50, "location": "Shelf C - Row 1", "barcode": "0000000000001"}'
```

## 3. Create it again, unchanged

Expect `200` — not `201` — and the **same** `id`. POST is idempotent on
`barcode`, so this updates the existing row instead of adding a duplicate.

```bash
curl -X POST http://localhost:8000/perfumes \
  -H "Content-Type: application/json" \
  -d '{"name": "Curl Test Scent", "brand": "ACME", "type": "Eau de Parfum", "gender": "unisex", "size": 50, "stock": 3, "price": 42.50, "location": "Shelf C - Row 1", "barcode": "0000000000001"}'
```

## 4. Same barcode, changed values

Expect `200`, the same `id`, and `price` now `99.0` with `stock` `1`. Only the
fields you send are written; anything omitted keeps its stored value.

```bash
curl -X POST http://localhost:8000/perfumes \
  -H "Content-Type: application/json" \
  -d '{"name": "Curl Test Scent", "brand": "ACME", "type": "Eau de Parfum", "gender": "unisex", "size": 50, "stock": 1, "price": 99.00, "location": "Shelf C - Row 1", "barcode": "0000000000001"}'
```

## 5. Reject an invalid body

Expect `422`. `stock` is declared `ge=0`, so `-5` is rejected before the
handler runs.

```bash
curl -X POST http://localhost:8000/perfumes \
  -H "Content-Type: application/json" \
  -d '{"name": "Curl Test Scent", "brand": "ACME", "type": "Eau de Parfum", "gender": "unisex", "size": 50, "stock": -5, "price": 42.50, "location": "Shelf C - Row 1", "barcode": "0000000000001"}'
```

## 6. Get one perfume

Expect `200`.

```bash
curl http://localhost:8000/perfumes/6
```

## 7. Get a perfume that does not exist

Expect `404` and `{"detail": "Perfume not found"}`.

```bash
curl http://localhost:8000/perfumes/999999
```

## 8. Get with a non-numeric id

Expect `422`. The path parameter is typed `int`, so `abc` never reaches the
handler.

```bash
curl http://localhost:8000/perfumes/abc
```

## 9. Update one field

Expect `200` with `stock` changed to `42` and every other field untouched.
PATCH uses `exclude_unset=True`, so omitted fields are left alone.

```bash
curl -X PATCH http://localhost:8000/perfumes/6 \
  -H "Content-Type: application/json" \
  -d '{"stock": 42}'
```

## 10. Update a perfume that does not exist

Expect `404`.

```bash
curl -X PATCH http://localhost:8000/perfumes/999999 \
  -H "Content-Type: application/json" \
  -d '{"stock": 42}'
```

## 11. Delete it

Expect `204` and an empty body.

```bash
curl -X DELETE http://localhost:8000/perfumes/6
```

## 12. Delete the same id again

Expect `204` again. DELETE is idempotent: a missing row is not an error, so a
retry after a dropped response gets the same answer as the first attempt.

```bash
curl -X DELETE http://localhost:8000/perfumes/6
```

## 13. Delete an id that never existed

Expect `204`.

```bash
curl -X DELETE http://localhost:8000/perfumes/999999
```

## 14. Confirm it is gone

Expect `404`.

```bash
curl http://localhost:8000/perfumes/6
```

---

## Seeing the status code

`curl` prints only the body by default, and steps 11-13 return no body at all,
so they look like nothing happened. Add `-i` to any command above to print the
status line and headers first:

```bash
curl -i -X DELETE http://localhost:8000/perfumes/6
```

Postman always shows the status code, so this is only needed on the command
line.

## Resetting the data

Steps 1-14 clean up after themselves. To get back to the seeded inventory at
any point:

```bash
uv run alembic downgrade base && uv run alembic upgrade head
```
