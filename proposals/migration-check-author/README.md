# Migration checks: payment, rental, film, customer, address

Pairs in `checks/` (`<name>.pg.sql` / `<name>.sf.sql`). All pass on the current migration (17/17).

| check (per table) | req | proves |
|---|---|---|
| `<t>_row_count` (all 5) | MIG-003 | `COUNT(*)` and distinct primary-key count are equal (missing, extra, duplicated rows) |
| `payment_monthly_counts`, `rental_monthly_counts` | MIG-003 | rows per UTC month of `payment_date` / `rental_date` match |
| `<t>_column_aggregates` (all 5) | MIG-004 | per column: null count, distinct count, min, max, sum |
| `<t>_row_hash` (all 5) | MIG-005 | md5 of every column per row, keyed by PK; output lists key plus hash, so a diff names the key |

Aggregate details: text min/max use `COLLATE "C"` and sum is total length; enum and uuid compared as lowercase text; timestamps as UTC microsecond text, sum of epoch microseconds; dates sum of days; arrays use size (min/max/sum); booleans count of true. `film.fulltext` is excluded; the virtual `length_hours` is compared by computed value.

Row hash encoding: each column is `0` if NULL, else `1 || length || ':' || text`, joined by `|`. Timestamps are UTC with 6 fractional digits; numerics are cast at their stored scale; arrays are `size#elements joined by chr(31)`.

## Defects not caught
- Differences only in `fulltext` (excluded by design), or in column types, constraints and nullability (MIG-002 territory).
- Rows and columns outside these five tables.
- Array element order is hashed, but a NULL element inside an array is skipped by `array_to_string` on both sides, so null versus missing elements is not distinguished (size is hashed, so the count still differs).
- Timestamp differences below 1 microsecond, which the type cannot hold.
- Aggregates alone miss offsetting or swapped values. Only the row hash catches those.
- `row_hash` can fail to catch an md5 collision (negligible).
- The checks read live data only; they do not test boundary cases absent from the data.
- A payment partition-key change that preserves month, count and the row hash would be seen only via the hash, which includes `payment_date`.
