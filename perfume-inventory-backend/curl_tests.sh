#!/usr/bin/env bash
# Manual smoke test of every /perfumes endpoint.
#
#   Terminal 1:  uv run fastapi dev main.py
#   Terminal 2:  ./curl_tests.sh
#
# Override the host with:  BASE=http://127.0.0.1:9000 ./curl_tests.sh
set -u

BASE="${BASE:-http://127.0.0.1:8000}"
BARCODE="0000000000001"   # test SKU, removed again at the end

bold() { printf '\n\033[1m%s\033[0m\n' "$1"; }
note() { printf '  \033[2m%s\033[0m\n' "$1"; }

# req <method> <path> [json body]
req() {
  local method="$1" path="$2" body="${3:-}"
  printf '  \033[36m%s %s\033[0m\n' "$method" "$path"
  if [ -n "$body" ]; then
    curl -sS -X "$method" "$BASE$path" \
      -H 'Content-Type: application/json' -d "$body" \
      -w '  -> HTTP %{http_code}\n'
  else
    curl -sS -X "$method" "$BASE$path" -w '  -> HTTP %{http_code}\n'
  fi
  echo
}

NEW_PERFUME=$(cat <<JSON
{"name": "Curl Test Scent", "brand": "ACME", "type": "Eau de Parfum",
 "gender": "unisex", "size": 50, "stock": 3, "price": 42.50,
 "location": "Shelf C - Row 1", "barcode": "$BARCODE"}
JSON
)

bold "1. GET /perfumes - list everything"
note "expect 200 and the seeded inventory"
req GET /perfumes

bold "2. POST /perfumes - create"
note "expect 201 and a database-assigned id"
req POST /perfumes "$NEW_PERFUME"

# Grab the id the server assigned, for the by-id calls below.
ID=$(curl -sS "$BASE/perfumes" \
     | tr '{' '\n' | grep "$BARCODE" | tr ',' '\n' | grep '"id"' | tr -dc '0-9')
note "created id = ${ID:-<none>}"

bold "3. POST /perfumes again, same barcode - idempotent"
note "expect 200 (not 201) and the SAME id: the row is updated, not duplicated"
req POST /perfumes "$NEW_PERFUME"

bold "4. POST /perfumes, same barcode, changed body - overwrite"
note "expect 200, same id, price now 99.00 and stock 1"
req POST /perfumes "$(echo "$NEW_PERFUME" | sed 's/42.50/99.00/; s/"stock": 3/"stock": 1/')"

bold "5. POST /perfumes - validation failure"
note "expect 422: stock has ge=0, so -5 is rejected before the handler runs"
req POST /perfumes "$(echo "$NEW_PERFUME" | sed 's/"stock": 3/"stock": -5/')"

bold "6. GET /perfumes/{id} - one row"
note "expect 200"
req GET "/perfumes/$ID"

bold "7. GET /perfumes/{id} - missing row"
note "expect 404 with a detail message"
req GET /perfumes/999999

bold "8. GET /perfumes/{id} - wrong type"
note "expect 422: the path param is an int, so 'abc' never reaches the handler"
req GET /perfumes/abc

bold "9. PATCH /perfumes/{id} - partial update"
note "expect 200, stock changed to 42, every other field untouched"
req PATCH "/perfumes/$ID" '{"stock": 42}'

bold "10. PATCH /perfumes/{id} - missing row"
note "expect 404"
req PATCH /perfumes/999999 '{"stock": 42}'

bold "11. DELETE /perfumes/{id} - remove it"
note "expect 204 and an empty body"
req DELETE "/perfumes/$ID"

bold "12. DELETE /perfumes/{id} - same id again"
note "expect 204 again: DELETE is idempotent, a missing row is not an error"
req DELETE "/perfumes/$ID"

bold "13. DELETE /perfumes/{id} - never existed"
note "expect 204"
req DELETE /perfumes/999999

bold "14. GET /perfumes/{id} - confirm it is gone"
note "expect 404"
req GET "/perfumes/$ID"

bold "Done. Inventory is back to its starting state."
req GET /perfumes
