#!/bin/sh
# Write the Snowflake key and a connections.toml for PAGILA_SVC from CI secrets, outside
# the checkout, and export the paths the connector, dbt, and Soda read.
# Needs: SNOWFLAKE_ACCOUNT, SNOWFLAKE_PRIVATE_KEY (PEM), RUNNER_TEMP, GITHUB_ENV.
set -eu
: "${SNOWFLAKE_ACCOUNT:?}" "${SNOWFLAKE_PRIVATE_KEY:?}"

dir="$RUNNER_TEMP/snowflake"
umask 077
mkdir -p "$dir"
printf '%s\n' "$SNOWFLAKE_PRIVATE_KEY" > "$dir/pagila_svc.p8"
cat > "$dir/connections.toml" <<TOML
[pagila]
account = "$SNOWFLAKE_ACCOUNT"
user = "PAGILA_SVC"
authenticator = "SNOWFLAKE_JWT"
private_key_file = "$dir/pagila_svc.p8"
role = "PAGILA_ROLE"
warehouse = "PAGILA_WH"
database = "PAGILA_MIG"
schema = "RAW"
TOML

{
  echo "SNOWFLAKE_HOME=$dir"
  echo "SNOWFLAKE_PRIVATE_KEY_PATH=$dir/pagila_svc.p8"
} >> "$GITHUB_ENV"
