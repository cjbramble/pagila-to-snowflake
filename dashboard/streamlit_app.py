"""Validation dashboard: sign-off verdicts, requirement status, test results, and loads.

Runs in Streamlit in Snowflake (deployed by `python -m reconcile.dashboard`). Reads only the
QA schema, which `reconcile.signoff`, `reconcile.record`, and `migrate.load` write.
"""

import os

import pandas as pd
import streamlit as st

QA = "PAGILA_MIG.QA"
STATUS_ORDER = ["FAIL", "INCOMPLETE", "PASS"]


def session():
    """The app's Snowflake session; outside Snowflake, the connection in $SNOWFLAKE_CONNECTION."""
    try:
        from snowflake.snowpark.context import get_active_session

        return get_active_session()
    except Exception:  # no active session: running locally
        from snowflake.snowpark import Session

        name = os.environ.get("SNOWFLAKE_CONNECTION", "pagila")
        return Session.builder.config("connection_name", name).create()


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    return session().sql(sql).to_pandas()


def utc(column: str) -> str:
    """Timestamp column as UTC text; Snowpark would otherwise convert it to the session zone."""
    return f"TO_VARCHAR(CONVERT_TIMEZONE('UTC', {column}), 'YYYY-MM-DD HH24:MI') AS {column}"


def table_exists(name: str) -> bool:
    found = query(f"SHOW TABLES LIKE '{name}' IN SCHEMA {QA}")
    return not found.empty


def colour_status(value: object) -> str:
    colours = {
        "PASS": "#2e7d32",
        "GO": "#2e7d32",
        "passed": "#2e7d32",
        "SUCCESS": "#2e7d32",
        "FAIL": "#c62828",
        "NO-GO": "#c62828",
        "failed": "#c62828",
        "fail": "#c62828",
        "error": "#c62828",
        "INCOMPLETE": "#ef6c00",
        "skipped": "#ef6c00",
    }
    return f"color: {colours[value]}; font-weight: 600" if value in colours else ""


def styled(df: pd.DataFrame, *columns: str):
    return df.style.map(colour_status, subset=list(columns))


st.set_page_config(page_title="Pagila validation", layout="wide")
st.title("Pagila → Snowflake validation")

if not table_exists("SIGNOFF_RUNS"):
    st.warning("No sign-off runs yet. Run `python -m reconcile.signoff` to record one.")
    st.stop()

runs = query(
    f"SELECT RUN_ID, {utc('RECORDED_AT')}, COMMIT_SHA, VERDICT FROM {QA}.SIGNOFF_RUNS "
    "ORDER BY RECORDED_AT DESC"
)
labels = {
    r.RUN_ID: f"{r.RECORDED_AT} UTC · {r.VERDICT} · {r.COMMIT_SHA}" for r in runs.itertuples()
}
run_id = st.sidebar.selectbox("Sign-off run", list(labels), format_func=labels.get)
run = runs[runs.RUN_ID == run_id].iloc[0]
in_run = f"WHERE RUN_ID = '{run_id}'"  # run_id comes from SIGNOFF_RUNS, not user input

gates = query(f"SELECT GATE, CRITERION, MET, DETAIL FROM {QA}.SIGNOFF_GATES {in_run} ORDER BY GATE")
reqs = query(
    f"SELECT REQUIREMENT, TITLE, LAYER, STATUS FROM {QA}.SIGNOFF_REQUIREMENTS {in_run} "
    "ORDER BY REQUIREMENT"
)
pytest = query(
    f"SELECT TEST_ID, REQUIREMENT, LAYER, OUTCOME, MESSAGE FROM {QA}.RECON_RESULTS {in_run}"
)
dbt = query(
    f"SELECT TEST_NAME, KIND, REQUIREMENT, STATUS, MESSAGE FROM {QA}.DBT_TEST_RESULTS {in_run}"
)
loads = query(
    f"""SELECT TABLE_NAME, STATUS, ROWS_EXTRACTED, ROWS_LOADED, DURATION_S, {utc("FINISHED_AT")}
    FROM {QA}.LOAD_LOG
    WHERE FINISHED_AT <= (SELECT RECORDED_AT FROM {QA}.SIGNOFF_RUNS {in_run})
    QUALIFY ROW_NUMBER() OVER (PARTITION BY TABLE_NAME ORDER BY FINISHED_AT DESC) = 1
    ORDER BY TABLE_NAME"""
)

# A test can trace to several requirements, so it has one row per requirement: count tests once.
pytest_tests = pytest.drop_duplicates("TEST_ID")
dbt_tests = dbt.drop_duplicates("TEST_NAME")

verdict, met = st.columns([1, 3])
verdict.metric("Recommendation", run.VERDICT)
verdict.caption(f"Commit `{run.COMMIT_SHA}` · {run.RECORDED_AT} UTC")
met.metric("Gate criteria met", f"{int(gates.MET.sum())}/{len(gates)}")

a, b, c, d = st.columns(4)
a.metric("Requirements passing", f"{(reqs.STATUS == 'PASS').sum()}/{len(reqs)}")
b.metric("pytest passed", f"{(pytest_tests.OUTCOME == 'passed').sum()}/{len(pytest_tests)}")
c.metric("dbt tests passed", f"{(dbt_tests.STATUS == 'passed').sum()}/{len(dbt_tests)}")
loaded_ok = (loads.STATUS == "SUCCESS") & (loads.ROWS_EXTRACTED == loads.ROWS_LOADED)
d.metric("Tables loaded clean", f"{int(loaded_ok.sum())}/{len(loads)}")

gates_tab, reqs_tab, failures_tab, loads_tab, history_tab = st.tabs(
    ["Gate", "Requirements", "Failures", "Loads", "History"]
)

with gates_tab:
    shown = gates.assign(MET=gates.MET.map({True: "PASS", False: "FAIL"}))
    st.dataframe(styled(shown, "MET"), hide_index=True, width="stretch")

with reqs_tab:
    by_layer = (
        reqs.groupby(["LAYER", "STATUS"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=STATUS_ORDER, fill_value=0)
    )
    st.subheader("Requirements by layer")
    st.bar_chart(by_layer, color=["#c62828", "#ef6c00", "#2e7d32"])

    tests_per_req = pd.concat(
        [
            pytest.groupby("REQUIREMENT").size().rename("PYTEST_TESTS"),
            dbt.groupby("REQUIREMENT").size().rename("DBT_TESTS"),
        ],
        axis=1,
    )
    table = reqs.join(tests_per_req, on="REQUIREMENT").fillna({"PYTEST_TESTS": 0, "DBT_TESTS": 0})
    layers = st.multiselect("Layer", sorted(reqs.LAYER.dropna().unique()))
    if layers:
        table = table[table.LAYER.isin(layers)]
    st.dataframe(styled(table, "STATUS"), hide_index=True, width="stretch")

with failures_tab:
    # Skipped counts too: the sign-off treats a skipped test as INCOMPLETE.
    failed_pytest = pytest[pytest.OUTCOME != "passed"]
    failed_dbt = dbt[dbt.STATUS != "passed"]
    if failed_pytest.empty and failed_dbt.empty:
        st.success("Every test passed in this run.")
    if not failed_pytest.empty:
        st.subheader(f"pytest ({failed_pytest.TEST_ID.nunique()} not passing)")
        st.dataframe(styled(failed_pytest, "OUTCOME"), hide_index=True, width="stretch")
    if not failed_dbt.empty:
        st.subheader(f"dbt ({failed_dbt.TEST_NAME.nunique()} not passing)")
        st.dataframe(styled(failed_dbt, "STATUS"), hide_index=True, width="stretch")

with loads_tab:
    st.caption("Latest load per table at the time of this sign-off run.")
    st.dataframe(styled(loads, "STATUS"), hide_index=True, width="stretch")
    st.bar_chart(loads.set_index("TABLE_NAME")[["DURATION_S"]])

with history_tab:
    st.subheader("Sign-off runs")
    st.dataframe(styled(runs, "VERDICT"), hide_index=True, width="stretch")

    st.subheader("Tests not passing per recorded run")
    st.caption(
        "pytest and dbt tests. Includes `reconcile.record` runs, which run pytest only and have "
        "no sign-off verdict."
    )
    history = query(
        f"""WITH TESTS AS (
            SELECT RUN_ID, RECORDED_AT, 'pytest ' || TEST_ID AS TEST, OUTCOME = 'passed' AS OK
            FROM {QA}.RECON_RESULTS
            UNION ALL
            SELECT RUN_ID, RECORDED_AT, 'dbt ' || TEST_NAME, STATUS = 'passed'
            FROM {QA}.DBT_TEST_RESULTS
        )
        SELECT RUN_ID, {utc("RECORDED_AT")},
            COUNT(DISTINCT TEST) AS TESTS,
            COUNT(DISTINCT IFF(OK, NULL, TEST)) AS NOT_PASSING
        FROM TESTS GROUP BY RUN_ID, RECORDED_AT ORDER BY RUN_ID"""
    )
    st.bar_chart(history.set_index("RUN_ID")[["NOT_PASSING"]])
    st.dataframe(history, hide_index=True, width="stretch")
