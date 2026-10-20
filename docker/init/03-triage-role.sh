#!/bin/sh
# Read-only login for the dq-triage agent: SELECT only, and every transaction read-only.
# The login name comes from TRIAGE_PGUSER, the same variable src/triage/query.py uses.
# Runs on first start of a fresh volume; for an existing volume run it by hand:
#   docker compose exec -T source-db sh /docker-entrypoint-initdb.d/03-triage-role.sh
set -eu

# :'name' quotes a value as a literal and :"name" as an identifier, so any login name is safe.
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
     -v triage_user="$TRIAGE_PGUSER" -v triage_password="$TRIAGE_PGPASSWORD" \
     -v db="$POSTGRES_DB" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'triage_user', :'triage_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'triage_user') \gexec
ALTER ROLE :"triage_user" PASSWORD :'triage_password';
ALTER ROLE :"triage_user" SET default_transaction_read_only = on;
ALTER ROLE :"triage_user" SET statement_timeout = '60s';
GRANT CONNECT ON DATABASE :"db" TO :"triage_user";
GRANT USAGE ON SCHEMA public TO :"triage_user";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO :"triage_user";
SQL
