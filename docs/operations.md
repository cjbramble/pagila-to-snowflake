# Cost and teardown

## Cost

Measured on this trial account on 2026-10-21, where compute is billed at $3.00 per credit (`ORGANIZATION_USAGE.RATE_SHEET_DAILY`). `ACCOUNT_USAGE` lags by hours, so recent runs show up late.

| Item | Measured |
|---|---|
| Project compute (2 days of building and testing) | 4.60 credits on `PAGILA_WH` (`CREDITS_USED_COMPUTE`), about $13.80 |
| Billed for the whole account | 6.34 credits (`METERING_DAILY_HISTORY.CREDITS_BILLED`), about $19; includes the pre-existing `COMPUTE_WH` and cloud services after Snowflake's daily adjustment |
| One CI full run | 3 min 42 s end to end; at most about 0.06 credits (XS bills 1 credit per running hour) |
| Storage | 73 MB in `PAGILA_MIG` (no storage charge on the rate sheet yet) |
| Cortex summary | about $0.0007 per call |

- **Most of the spend is idle time.** Only about 1.5 of the 4.6 compute credits are attributed to queries. The rest is the 60-second minimum each time the warehouse resumes, plus the 60 seconds before it auto-suspends, paid on every short burst of tests. Attribution in `ACCOUNT_USAGE` also lags by hours.
- **Dashboard:** the Streamlit app runs on `PAGILA_WH` (warehouse runtime), so it bills only while someone has it open and counts toward `PAGILA_MONITOR`. Close the tab when done; the warehouse auto-suspends after its session ends.
- **Biggest query consumers:** the loader, pytest suite, and fault harnesses (`pagila-migration` tag, 0.69 credits), Soda (0.53), dbt mutations (0.14).
- **Guardrails:**
  - `PAGILA_MONITOR` allows 20 credits a month on `PAGILA_WH`. It notifies at 50% and 75% and suspends at 90%.
  - `ACCOUNT_MONITOR` allows 50 credits a month across every warehouse in the account and suspends at 90%.
  - Every warehouse auto-suspends after 60 seconds.

## Teardown

1. **Stop spending.** In Snowsight: `ALTER WAREHOUSE PAGILA_WH SUSPEND;`. "Invalid state ... cannot be suspended" means it already is. Check `SHOW WAREHOUSES;` for anything else still `STARTED`.
2. **Check what it cost:**
   ```sql
   SHOW RESOURCE MONITORS;   -- used_credits per monitor this month
   -- What was billed, per day and service (cloud services after the daily adjustment)
   SELECT USAGE_DATE, SERVICE_TYPE, ROUND(SUM(CREDITS_BILLED), 3)
   FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY GROUP BY 1, 2 ORDER BY 1, 2;
   -- Warehouse compute per warehouse (CREDITS_USED would add unadjusted cloud services)
   SELECT WAREHOUSE_NAME, ROUND(SUM(CREDITS_USED_COMPUTE), 3)
   FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY GROUP BY 1;   -- lags up to 3 h
   ```
3. **Drop the project:** run [sql/snowflake_teardown.sql](../sql/snowflake_teardown.sql) as ACCOUNTADMIN.
   - It drops the database (every schema, including `FAULTS` and `MUT_*`, and the dashboard app), the warehouse, both users, both roles, and `PAGILA_MONITOR`.
   - `UNDROP DATABASE PAGILA_MIG` works for 1 day (Time Travel). After that the database spends 7 days in Fail-safe, recoverable only by Snowflake support and still billed for storage, then it's purged.
   - It leaves `ACCOUNT_MONITOR` and anything that predates the project.
4. **Local:**
   - `docker compose down -v` deletes the source container and its volume.
   - Delete `~/.snowflake/pagila_rsa_key.*` and `~/.snowflake/pagila_triage_rsa_key.*`.
   - Remove `[pagila]` and `[pagila_triage]` from `connections.toml`, and delete `.env`.
5. **GitHub:** `gh secret delete SNOWFLAKE_ACCOUNT` and `gh secret delete SNOWFLAKE_PRIVATE_KEY`.
