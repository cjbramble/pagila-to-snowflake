-- One-time account setup for the Pagila migration project.
-- Run in Snowsight as ACCOUNTADMIN, top to bottom. Safe to re-run.
-- Existing objects (RECON_PRACTICE, COMPUTE_WH, ...) are left alone apart from
-- the auto-suspend and account monitor guardrails at the end.
-- Before running: replace <PASTE_PUBLIC_KEY_HERE> with the body of your public key
-- (the lines between BEGIN/END PUBLIC KEY, joined into one line).

-- Roles and users: USERADMIN creates them, SECURITYADMIN grants them.
USE ROLE USERADMIN;

CREATE ROLE IF NOT EXISTS PAGILA_ROLE
    COMMENT = 'Owns and runs the Pagila migration project';

-- Granting to SYSADMIN keeps the role in the standard hierarchy,
-- so admins can see and manage everything it creates.
USE ROLE SECURITYADMIN;
GRANT ROLE PAGILA_ROLE TO ROLE SYSADMIN;

-- Compute
USE ROLE SYSADMIN;

CREATE WAREHOUSE IF NOT EXISTS PAGILA_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    STATEMENT_TIMEOUT_IN_SECONDS = 600
    COMMENT = 'Pagila migration: loads, reconciliation, dbt';

GRANT USAGE, OPERATE ON WAREHOUSE PAGILA_WH TO ROLE PAGILA_ROLE;

-- Storage: the project role owns the database so the loader and dbt
-- can create and replace objects without per-object grants.
CREATE DATABASE IF NOT EXISTS PAGILA_MIG
    COMMENT = 'Pagila migration target';

GRANT OWNERSHIP ON DATABASE PAGILA_MIG TO ROLE PAGILA_ROLE COPY CURRENT GRANTS;

USE ROLE PAGILA_ROLE;
USE DATABASE PAGILA_MIG;

CREATE SCHEMA IF NOT EXISTS RAW     COMMENT = 'Landed copy of the Postgres source';
CREATE SCHEMA IF NOT EXISTS STAGING COMMENT = 'dbt staging models over RAW';
CREATE SCHEMA IF NOT EXISTS MARTS   COMMENT = 'dbt business marts';
CREATE SCHEMA IF NOT EXISTS QA      COMMENT = 'Load logs, reconciliation results';

-- Service user: key-pair only. TYPE = SERVICE blocks password and MFA login.
USE ROLE USERADMIN;

CREATE USER IF NOT EXISTS PAGILA_SVC
    TYPE = SERVICE
    DEFAULT_ROLE = PAGILA_ROLE
    DEFAULT_WAREHOUSE = PAGILA_WH
    DEFAULT_NAMESPACE = PAGILA_MIG.RAW
    RSA_PUBLIC_KEY = '<PASTE_PUBLIC_KEY_HERE>'
    COMMENT = 'Loader, tests and dbt for the Pagila project';

USE ROLE SECURITYADMIN;
GRANT ROLE PAGILA_ROLE TO USER PAGILA_SVC;

-- Cost guardrail. 20 credits is roughly 20 hours of X-Small, a small share of
-- the trial. Resource monitors only cover warehouse compute, not serverless
-- or Cortex AI usage; those are checked separately in Phase 7.
USE ROLE ACCOUNTADMIN;

CREATE OR REPLACE RESOURCE MONITOR PAGILA_MONITOR
    WITH CREDIT_QUOTA = 20
    FREQUENCY = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS
        ON 50 PERCENT DO NOTIFY
        ON 75 PERCENT DO NOTIFY
        ON 90 PERCENT DO SUSPEND
        ON 100 PERCENT DO SUSPEND_IMMEDIATE;

ALTER WAREHOUSE PAGILA_WH SET RESOURCE_MONITOR = PAGILA_MONITOR;

-- Backstop for every warehouse in the account, including ones created outside
-- this project. Suspends only, never notifies early: PAGILA_MONITOR does that.
CREATE OR REPLACE RESOURCE MONITOR ACCOUNT_MONITOR
    WITH CREDIT_QUOTA = 50
    FREQUENCY = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS
        ON 90 PERCENT DO SUSPEND
        ON 100 PERCENT DO SUSPEND_IMMEDIATE;

ALTER ACCOUNT SET RESOURCE_MONITOR = ACCOUNT_MONITOR;

-- The pre-existing trial warehouses default to 300s; idle time is billed.
ALTER WAREHOUSE IF EXISTS COMPUTE_WH SET AUTO_SUSPEND = 60;
ALTER WAREHOUSE IF EXISTS SNOWFLAKE_LEARNING_WH SET AUTO_SUSPEND = 60;

-- Verify
SHOW WAREHOUSES;
SHOW RESOURCE MONITORS;
SHOW SCHEMAS IN DATABASE PAGILA_MIG;
DESC USER PAGILA_SVC;
