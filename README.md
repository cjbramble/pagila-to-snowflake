# Pagila → Snowflake migration QA

A small, realistic data-migration test program: migrate the Pagila sample database from PostgreSQL 18 to Snowflake, then prove the migration with layered, requirement-traced reconciliation.

## Run it

```bash
docker compose up -d                                        # source Postgres on localhost:5434
uv run --env-file .env python -m migrate.load               # migrate all tables to PAGILA_MIG.RAW
uv run --env-file .env pytest                               # spec, loader, and reconciliation suite
uv run --env-file .env python -m faults.matrix              # inject each fault, score detection (~8 min)
```

Setup (Snowflake account, key pair, `.env`) is covered in `sql/snowflake_setup.sql` and `.env.example`.

## Reconciliation layers

Cheap to expensive. Each test is tagged with a requirement in `requirements/requirements.yml`, and pytest prints a per-requirement summary.

| Layer | Requirement | What it compares | Catches |
|---|---|---|---|
| Spec | MIG-001 | Mapping spec vs live source catalog | Unmapped columns, source type drift |
| Schema | MIG-002 | `DESC TABLE` vs spec: names, order, types, nullability, virtual, CHECK, PK | Wrong DDL, missing constraints |
| Volume | MIG-003, MIG-006 | Row counts per table; latest load log entry per table | Dropped or duplicated loads, failed runs |
| Aggregate | MIG-004 | Per column: nulls, distinct, min, max, sum | Truncation, shifted values, wrong types |
| Row | MIG-005 | Normalized MD5 per primary key, both sides | Any changed, missing, or extra row, reported by key |
| Integrity | MIG-007, MIG-008 | Orphans for 23 relationships; domain rules | Broken references (Snowflake doesn't enforce FKs) |
| Contract | MIG-009 | Soda contracts on key RAW tables | Rule violations in the target itself |

## Soda Core vs the custom pytest layer

| | Soda Core v4 (open source) | Custom pytest |
|---|---|---|
| Model | Declarative YAML contract per dataset | Python tests generated from the mapping spec |
| Compares source to target | **No.** Reconciliation checks (`row_count_diff`, `rows_diff`, ...) need the licensed `soda-reconciliation` package | Yes: counts, aggregates, and row hashes across both systems |
| Good at | Readable rules on one dataset: missing, duplicates, valid values, ranges, schema shape | Exact cross-dialect equality, with the offending keys in the failure |
| Dialect handling | Hidden inside Soda | Explicit and reviewable (UTC, collation, enum ordering, null tokens) |
| Setup cost | Data source YAML + contract per table; no code | More code; owns every normalization decision |

Takeaway: use Soda contracts as the target's ongoing data-quality guardrail, owned by the data team. Use the pytest reconciliation to sign off the migration itself.

## Row-hash normalization

Hand-written for `payment` in `sql/reconciliation/` (both dialects), generalized in `src/reconcile/rowhash.py`. A test proves the generator matches the hand-written pair row for row.

- NULL is encoded as `0` and a value as `1` + value. A `\N` token doesn't work, because Snowflake reads `'\N'` as `N`.
- Timestamps are UTC with microseconds. Numerics use fixed scale. UUIDs are lowercase.
- Strings are compared untrimmed. Pagila has no `CHAR(n)` columns, so trimming could only hide defects.
- Vectors are rounded to 9 decimals per element: no false mismatches on the 1,000 real embeddings, and a 1e-7 drift is caught.
