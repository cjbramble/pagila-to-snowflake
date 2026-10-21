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
uv run --env-file .env python -m faults.dbt_mutations       # break dbt models 17 ways, score the dbt tests
uv run --env-file .env python -m faults.pair_matrix DIR     # score a folder of paired SQL checks against the faults
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
| Code review | Codex (a different model) on PRs #1 and #2 | The human accepted 8 findings and kept 1 design choice |

Almost all code and SQL here is AI-generated. The project's point is proving it correct, and [AI_LOG.md](AI_LOG.md) records every defect found in AI output, with what caught it (39 so far).

### Agents in the QA workflow

Four focused Claude Code subagents (`.claude/agents/`). Each one was evaluated blind against ground truth before being trusted.

| Agent | Job | How it was scored | Result |
|---|---|---|---|
| `dq-triage` | Diagnose a failing check: affected rows, pattern, root cause, fix, earliest catching test | 4 randomly drawn faults, given only the failing output | 31/32; it found a real gap (MIG-006 now recounts tables) |
| `dbt-test-author` | Write dbt unit, data, and singular tests from a model and its ETL rules | 17 model mutations, against the existing tests | 17/17 vs 16/17; **found a real precision bug** in `mart_rental_returns`, now fixed |
| `migration-check-author` | Write paired Postgres/Snowflake validation SQL for tables and MIG requirements | False alarms on clean data, then the 12-fault matrix | 0/17 false alarms; 10/12 faults (all 10 in its brief); two of its ideas were ported into `src/reconcile` |
| `rule-reviewer` | Find the ambiguities in a draft business rule before it's built | Recall against 13 gaps settled in this project | 12.5/13 recall, 14/14 precision, every count exact; found SRC-005 |

How the agents are kept honest:
- **Read-only database access.** Agents query only through `triage.query`, `triage.check_pair`, and `triage.dbt_check`, as Postgres `dq_triage` and Snowflake `PAGILA_TRIAGE_SVC`. Writes were rejected on both, even with read-only mode forced off. `triage.dbt_check` overlays only test files and always uses this repo's profile, so a proposal can't switch to a writable login.
- **Proposals, not edits.** Authors write only to `proposals/<agent>/`. A human reviews the output and promotes what's good into the suite.
- **Blind evaluation.** Workspaces are stripped of the existing tests and answers and checked for leaks; scores come from mutation and fault harnesses (`faults.dbt_mutations`, `faults.pair_matrix`, `faults.matrix`).
- **One shared rule set.** Every agent follows [docs/dq_checklist.md](docs/dq_checklist.md), the traps behind the defects in [AI_LOG.md](AI_LOG.md).

Other AI in the pipeline:
- **AI-generated validation SQL:** written from requirement IDs and human-reviewed. 5 defects, one a latent `DATEDIFF` bug (`reports/ai_sql_review.md`).
- **Cortex `AI_SUMMARIZE_AGG`:** summarizes a recorded run's failures, and the summary is fact-checked for invented or omitted facts. It's the only AI function a trial account allows, at about $0.0007 per call.

Setup for the read-only identities: `docker/init/03-triage-role.sh` (Postgres) and `sql/snowflake_triage_reader.sql` (Snowflake, run as ACCOUNTADMIN). New agent files load only after restarting Claude Code.

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

- NULL is encoded as `0` and a value as `1` + its length + `:` + the value. A `\N` token doesn't work, because Snowflake reads `'\N'` as `N`. The length prefix makes the encoding unambiguous: a separator alone lets two different rows produce the same text.
- Timestamps are UTC with microseconds. Numerics use fixed scale. UUIDs are lowercase.
- Strings are compared untrimmed. Pagila has no `CHAR(n)` columns, so trimming could only hide defects.
- Vectors are rounded to 9 decimals per element: no false mismatches on the 1,000 real embeddings, and a 1e-7 drift is caught.
