# Pagila → Snowflake migration QA

A small, realistic data-migration test program: migrate the Pagila sample database from PostgreSQL 18 to Snowflake, then prove the migration with layered, requirement-traced reconciliation.

## Run it

```bash
docker compose up -d                                        # source Postgres on localhost:5434
uv run --env-file .env python -m migrate.load               # migrate all tables to PAGILA_MIG.RAW
(cd dbt && uv run --env-file ../.env dbt build --profiles-dir .)   # staging + marts, unit and data tests
uv run --env-file .env pytest                               # spec, loader, reconciliation, ETL suite
uv run --env-file .env python -m faults.matrix              # inject each fault, score detection (~8 min)
uv run --env-file .env python -m reconcile.record           # store a suite run in QA.RECON_RESULTS
uv run --env-file .env python -m reconcile.summarize        # Cortex summary of its failures, fact-checked
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
| Business rule | ETL-001 to ETL-007 | dbt unit tests (edge cases), dbt data tests, and marts vs an independent Postgres implementation | Wrong rule logic, boundary errors, join fan-out or loss |
| Mart contract | ETL-008 | Soda contracts on the three marts | Grain, value sets, fee consistency for consumers |

## dbt marts

| Mart | Grain | Rules |
|---|---|---|
| `MARTS.MART_MONTHLY_STORE_REVENUE` | store × UTC month | ETL-001, ETL-002 |
| `MARTS.MART_CUSTOMER_LIFETIME_VALUE` | customer | ETL-003 |
| `MARTS.MART_RENTAL_RETURNS` | rental | ETL-004 to ETL-007: due date, status, days late, late fee |

Rules are written in plain English in `requirements/requirements.yml`. Every dbt test declares its rule in `config.meta.requirement`, and `tests/test_etl_traceability.py` fails if a rule has no dbt test.

## AI in the workflow

### Who authored what

| Artifact | Written by | Validated by |
|---|---|---|
| Profiling SQL, mapping spec, loader, DDL generator | Claude Code (AI) | The human (all 9 mapping decisions), plus live probes in Snowflake |
| Reconciliation layers, row-hash SQL, Soda contracts | Claude Code | Cross-checks with differently shaped queries, negative controls, the fault matrix |
| dbt models, unit/data/singular tests | Claude Code | The human (business-rule decisions), model mutations, an independent Postgres re-implementation |
| Fault injector and matrix | Claude Code | Predictions written down before each run, verified restores |
| Requirements and business rules | Claude Code drafts | The human decides every judgement call (edge cases, attribution, rounding) |
| Code review | Codex (a different model) on PR #1 | The human accepted 3 findings and kept 1 design choice |

Almost all code and SQL here is AI-generated. The project's point is proving it correct, and [AI_LOG.md](AI_LOG.md) records every defect found in AI output, with what caught it (27 so far).

### Agents and AI features in the pipeline

| Piece | What it does | Evidence |
|---|---|---|
| `dq-triage` agent (`.claude/agents/`) | Given failing check output, queries both databases and reports the affected rows, pattern, root cause, fix, and the earliest catching check | Blind test on 4 random faults: 31/32, compliance 4/4 (`AI_LOG.md`) |
| Read-only access (`src/triage/query.py`) | The agent's only database tool: Postgres `dq_triage` and Snowflake `PAGILA_TRIAGE_SVC`, both SELECT-only | Writes rejected on both databases, including with read-only mode forced off |
| AI-generated SQL | Validation queries written from requirement IDs, then human-reviewed | 5 defects, one latent `DATEDIFF` bug (`reports/ai_sql_review.md`) |
| Cortex `AI_SUMMARIZE_AGG` | Summarizes a recorded run's failures; output is fact-checked for invented or omitted facts | The only AI function a trial account allows; about $0.0007 per call |

Setup for the agent's identities: `docker/init/03-triage-role.sh` (Postgres) and `sql/snowflake_triage_reader.sql` (Snowflake, run as ACCOUNTADMIN).

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
