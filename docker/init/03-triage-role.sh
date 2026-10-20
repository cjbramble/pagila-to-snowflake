#!/bin/sh
# Read-only login for the dq-triage agent: SELECT only, and every transaction read-only.
# Runs on first start of a fresh volume; for an existing volume run it by hand:
#   docker compose exec -T source-db sh /docker-entrypoint-initdb.d/03-triage-role.sh
set -eu

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
     -v triage_password="$TRIAGE_PGPASSWORD" <<'SQL'
SELECT format('CREATE ROLE dq_triage LOGIN PASSWORD %L', :'triage_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dq_triage') \gexec
ALTER ROLE dq_triage PASSWORD :'triage_password';
ALTER ROLE dq_triage SET default_transaction_read_only = on;
ALTER ROLE dq_triage SET statement_timeout = '60s';
GRANT CONNECT ON DATABASE pagila TO dq_triage;
GRANT USAGE ON SCHEMA public TO dq_triage;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dq_triage;
SQL
