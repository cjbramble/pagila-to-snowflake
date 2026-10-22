"""Deploy the validation dashboard (dashboard/) to Streamlit in Snowflake.

Uploads the app files to a stage in QA and (re)creates the Streamlit object. It uses the
warehouse runtime, so the app runs on PAGILA_WH only while someone has it open, under
PAGILA_MONITOR, with the packages pinned in dashboard/environment.yml. (The account default,
the container runtime, bills a compute pool the monitor doesn't cover and ignores that file.)

Usage: python -m reconcile.dashboard   (prints the app's Snowsight URL)
"""

from migrate.snowflake_conn import connect
from reconcile.results import ROOT
from reconcile.store import QA

APP_DIR = ROOT / "dashboard"
FILES = ["streamlit_app.py", "environment.yml"]
STAGE = f"{QA}.DASHBOARD_STAGE"
APP = f"{QA}.VALIDATION_DASHBOARD"
WAREHOUSE = "PAGILA_WH"


def main() -> None:
    with connect() as sf:
        cur = sf.cursor()
        cur.execute(f"CREATE STAGE IF NOT EXISTS {STAGE}")
        for name in FILES:
            cur.execute(
                f"PUT 'file://{APP_DIR / name}' @{STAGE} AUTO_COMPRESS = FALSE OVERWRITE = TRUE"
            )
        cur.execute(
            f"""CREATE OR REPLACE STREAMLIT {APP}
            FROM '@{STAGE}'
            MAIN_FILE = 'streamlit_app.py'
            RUNTIME_NAME = 'SYSTEM$WAREHOUSE_RUNTIME'
            QUERY_WAREHOUSE = {WAREHOUSE}
            TITLE = 'Pagila validation'"""
        )
        org, account = cur.execute(
            "SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME()"
        ).fetchone()
    print(
        f"deployed {APP}: https://app.snowflake.com/{org.lower()}/{account.lower()}"
        f"/#/streamlit-apps/{APP}"
    )


if __name__ == "__main__":
    main()
