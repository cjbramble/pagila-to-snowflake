-- Removes everything this project created in Snowflake. Run in Snowsight as ACCOUNTADMIN,
-- top to bottom, only when you're done with the project: you can undo the database drop
-- only within its 1-day Time Travel window.
--
-- Not touched: objects that predate the project (COMPUTE_WH, RECON_PRACTICE, ...) and the
-- account-wide ACCOUNT_MONITOR guardrail (optional block at the end).

USE ROLE ACCOUNTADMIN;

-- Stop new spend first, so nothing resumes the warehouse mid-teardown.
ALTER WAREHOUSE IF EXISTS PAGILA_WH SET AUTO_RESUME = FALSE;

-- Every schema (RAW, STAGING, MARTS, QA, FAULTS, MUT_STAGING, MUT_MARTS), the stage, file
-- format, tables, and views. UNDROP DATABASE PAGILA_MIG works for 1 day; then 7 days of
-- Fail-safe (recoverable only by Snowflake support, storage still billed), then purged.
DROP DATABASE IF EXISTS PAGILA_MIG;

DROP WAREHOUSE IF EXISTS PAGILA_WH;
DROP RESOURCE MONITOR IF EXISTS PAGILA_MONITOR;

DROP USER IF EXISTS PAGILA_SVC;
DROP USER IF EXISTS PAGILA_TRIAGE_SVC;
DROP ROLE IF EXISTS PAGILA_TRIAGE;
DROP ROLE IF EXISTS PAGILA_ROLE;

-- Expect no rows from each.
SHOW DATABASES LIKE 'PAGILA%';
SHOW WAREHOUSES LIKE 'PAGILA%';
SHOW USERS LIKE 'PAGILA%';
SHOW ROLES LIKE 'PAGILA%';
SHOW RESOURCE MONITORS LIKE 'PAGILA%';

-- Optional: remove the account-wide credit guardrail too. It caps every warehouse in the
-- account, not just this project's, so it's safer to keep while the trial is active.
-- DROP RESOURCE MONITOR IF EXISTS ACCOUNT_MONITOR;
