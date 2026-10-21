# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A data QA project: Pagila is migrated from PostgreSQL 18 to Snowflake (`PAGILA_MIG.RAW`), with dbt marts on top (`STAGING`, `MARTS`). The migration and the marts are the system under test. The real product is the validation suite: requirement-traced reconciliation, Soda contracts, dbt business-rule tests, fault injection, and a go/no-go sign-off gate. See `README.md` for setup, cost, and teardown.

## Commands

Run everything with `uv`. Commands that touch either database need `--env-file .env`.

```bash
docker compose up -d                                         # source Postgres (pgvector PG18) on localhost:5434
uv run --env-file .env python -m migrate.load [TABLE ...]    # full-refresh load to RAW, logs to QA.LOAD_LOG
(cd dbt && uv run --env-file ../.env dbt build --profiles-dir .)   # dbt must run from dbt/ with --profiles-dir .
uv run --env-file .env pytest                                # full suite (needs Postgres + Snowflake)
uv run --env-file .env pytest -m "not target_db"             # what CI runs (CI sets PG* itself): no Snowflake needed
uv run --env-file .env pytest tests/reconciliation/test_04_rows.py -k payment   # single test
uv run ruff format --check . && uv run ruff check .          # lint, as CI does
uv run --env-file .env python -m reconcile.signoff           # run everything, write reports/migration_signoff.md; exit 1 on NO-GO
```

Harnesses (slow, write to Snowflake):
- `python -m faults.matrix [FAULT ...]` injects each fault into RAW, runs `tests/reconciliation`, restores from a zero-copy clone in `PAGILA_MIG.FAULTS`, and writes `reports/fault_matrix.md` (~8 min).
- `python -m faults.dbt_mutations` mutates dbt models and builds them with the `mutation` target into `MUT_*` schemas.
- `python -m faults.pair_matrix DIR` scores a folder of paired `.pg.sql`/`.sf.sql` checks against the faults.

## Architecture

- **The mapping spec drives everything.** `mapping/type_mapping.yml` is the column-by-column Postgres → Snowflake spec (types, nullability, virtual columns, CHECKs, exclusions, decision IDs). `migrate.ddl` generates DDL from it, `migrate.load` loads from it, and the schema, aggregate, and row-hash layers compare against it. Changing a column means changing the spec first.
- **Requirements are the trace key.** `requirements/requirements.yml` defines `MIG-*`, `ETL-*`, and known source issues `SRC-*`. Tests that verify a requirement (reconciliation, ETL, mapping spec) carry `@pytest.mark.req("...")`; collection fails on an unknown ID (`tests/conftest.py`), and pytest prints a per-requirement summary. Unit and harness tests (`test_loader`, `test_rowhash`, `test_summarize`, `test_qa_tools`, `test_etl_traceability`) carry none, and the sign-off gate covers them through G5; don't add a requirement just to mark a test. Every dbt test declares `config.meta.requirement`; `tests/test_etl_traceability.py` fails if an ETL rule has no dbt test. Each requirement's `layer` field is how the fault matrix groups results.
- **Reconciliation layers** live in `tests/reconciliation/test_0N_*.py` (schema → volume → aggregates → rows → integrity → Soda), backed by `src/reconcile/`. A conftest there marks all of them `source_db` + `target_db`.
- **Row hashing** (`src/reconcile/rowhash.py`) generalizes the hand-written pair in `sql/reconciliation/`; a test proves they match. Its normalization rules (length-prefixed values, `0` for NULL, UTC microseconds, 9-decimal vectors) are explained in the README.
- **Sign-off gate** (`reconcile.signoff`) runs pytest + `dbt test` once, reads the latest `QA.LOAD_LOG` per table, and applies the human decisions in `requirements/signoff.yml` (dispositions per `SRC-*`, waivers). Any `pending` disposition means NO-GO.
- **Connections:** Snowflake connects through `~/.snowflake/connections.toml` (`migrate.snowflake_conn.connect`, connection from `$SNOWFLAKE_CONNECTION`, session pinned to UTC). Postgres uses standard `PG*` env vars. Soda and dbt can't read `connections.toml`, so they use `SNOWFLAKE_ACCOUNT` and the key-path env vars.
- **dbt targets** (`dbt/profiles.yml`): `dev` builds the real schemas; `readonly` is the SELECT-only triage identity; `mutation` builds into `MUT_*` via `macros/generate_schema_name.sql`, so mutations never overwrite real marts.

## AI agents and proposals

- Subagents in `.claude/agents/` (`dq-triage`, `dbt-test-author`, `migration-check-author`, `rule-reviewer`) query only through `triage.query`, `triage.check_pair`, and `triage.dbt_check`, as read-only identities (Postgres `dq_triage`, Snowflake `PAGILA_TRIAGE_SVC`).
- Authoring agents write only to `proposals/<agent>/`. A human promotes what's good into the suite.
- `docs/dq_checklist.md` holds the Postgres ↔ Snowflake traps found in this project (DATEDIFF boundaries, `COLLATE "C"`, backslash literals, LA default time zone, CHECK blocking `COPY INTO`, unenforced PKs/FKs). Follow it when writing any cross-system SQL or test.

## Project conventions

- **AI generates, the human validates.** Every generated artifact needs proof before it's accepted: a cross-check with a differently shaped query, a negative control, or a live probe of Snowflake instead of recalled API knowledge. The human makes every judgement call (mapping decisions, rule edge cases, dispositions).
- **Log defects in AI output** in `AI_LOG.md` (numbered defect table: artifact, defect, what caught it, fix). Add a rule to `docs/dq_checklist.md` when a defect reveals a reusable trap.
- Reports that start with "Generated ... by `python -m ...`" (sign-off, fault, mutation, pair-check matrices) come from the harnesses: regenerate them, don't hand-edit them. `ai_sql_review.md` and `source_profile.md` are written by hand.
- CI (`ci.yml`) and the full run (`full-run.yml`) use the same `pgvector/pgvector:0.8.7-pg18-trixie` image as `docker-compose.yml`. Keep them in sync.
