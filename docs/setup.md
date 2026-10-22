# Setup and commands

## One-time setup

Snowsight steps run as ACCOUNTADMIN.

1. Install Docker, `uv`, and git, and start a Snowflake trial.
2. Create two key pairs (service user and read-only agent user):
   ```bash
   mkdir -p ~/.snowflake
   for k in pagila pagila_triage; do
     openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out ~/.snowflake/${k}_rsa_key.p8 -nocrypt
     openssl rsa -in ~/.snowflake/${k}_rsa_key.p8 -pubout -out ~/.snowflake/${k}_rsa_key.pub
     chmod 600 ~/.snowflake/${k}_rsa_key.p8
   done
   ```
3. In Snowsight, paste each public key into its script and run `sql/snowflake_setup.sql`, then `sql/snowflake_triage_reader.sql`.
4. Add both connections to `~/.snowflake/connections.toml`:
   ```toml
   [pagila]
   account = "<org>-<account>"
   user = "PAGILA_SVC"
   authenticator = "SNOWFLAKE_JWT"
   private_key_file = "/Users/<you>/.snowflake/pagila_rsa_key.p8"
   role = "PAGILA_ROLE"
   warehouse = "PAGILA_WH"
   database = "PAGILA_MIG"
   schema = "RAW"

   [pagila_triage]
   account = "<org>-<account>"
   user = "PAGILA_TRIAGE_SVC"
   authenticator = "SNOWFLAKE_JWT"
   private_key_file = "/Users/<you>/.snowflake/pagila_triage_rsa_key.p8"
   role = "PAGILA_TRIAGE"
   warehouse = "PAGILA_WH"
   database = "PAGILA_MIG"
   schema = "RAW"
   ```
5. `cp .env.example .env` and fill it in, then `uv sync` and `docker compose up -d`.

## Commands

```bash
docker compose up -d                                        # source Postgres on localhost:5434
uv run --env-file .env python -m migrate.load               # migrate all tables to PAGILA_MIG.RAW
(cd dbt && uv run --env-file ../.env dbt build --profiles-dir .)   # staging + marts, unit and data tests
uv run --env-file .env pytest                               # spec, loader, reconciliation, ETL suite
uv run --env-file .env python -m faults.matrix              # inject each fault, score detection (~8 min)
uv run --env-file .env python -m reconcile.record           # store a suite run in QA.RECON_RESULTS
uv run --env-file .env python -m reconcile.summarize        # Cortex summary of its failures, fact-checked
uv run --env-file .env python -m faults.dbt_mutations       # break dbt models 17 ways, score the dbt tests
uv run --env-file .env python -m faults.pair_matrix sql/checks   # score the paired SQL checks against the faults
uv run --env-file .env python -m reconcile.signoff          # run everything, write reports/migration_signoff.md (exit 1 on NO-GO)
```

## CI

| Workflow | Runs on | What it does | Needs |
|---|---|---|---|
| `.github/workflows/ci.yml` | every PR, pushes to `main` | ruff, then `pytest -m "not target_db"` (31 tests: mapping spec vs a live Pagila source, loader, row-hash, harness and gate unit tests, dbt traceability) against a PostgreSQL 18 + pgvector service container | nothing |
| `.github/workflows/full-run.yml` | manual (`workflow_dispatch`) | fresh source → `migrate.load` → `dbt build` → `reconcile.signoff`; fails on NO-GO and keeps the sign-off report as an artifact | repo secrets `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_PRIVATE_KEY` |

Tests that need Snowflake are marked `target_db`. The full run overwrites `RAW`, `STAGING`, and `MARTS`; the first one took 3 min 42 s end to end.

The full run needs two repository secrets: `SNOWFLAKE_ACCOUNT` and `SNOWFLAKE_PRIVATE_KEY` (the service user's unencrypted PEM key).
