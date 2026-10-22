"""Run every check once and write the migration sign-off report with a go/no-go gate.

One run, so every result in the report comes from the same moment:
  - the whole pytest suite (spec, schema, volume, aggregate, row, integrity, contracts, ETL)
  - dbt test (unit and data tests on the built marts; nothing is built or changed)
  - the latest QA.LOAD_LOG entry per table
The verdict depends only on test results: coverage, requirement status, and untraced tests.
Human decisions come from requirements/signoff.yml: waivers count toward the verdict;
known-issue dispositions are reported but don't affect it.

The verdict, gates, requirement statuses, and every pytest and dbt result are also stored
in the QA schema under one run ID, for the dashboard (dashboard/).

Exits 0 on GO and 1 on NO-GO, so CI can use it as the gate.

Usage: python -m reconcile.signoff [--report PATH]
"""

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from migrate.mapping import load_spec
from migrate.snowflake_conn import connect
from reconcile.results import (
    REQUIREMENTS,
    REQUIREMENTS_FILE,
    ROOT,
    requirement_status,
    run_pytest,
)
from reconcile.store import insert, new_run_id, store_dbt, store_pytest

KNOWN_ISSUES = REQUIREMENTS_FILE["known_source_issues"]
SIGNOFF_FILE = ROOT / "requirements" / "signoff.yml"
DEFAULT_REPORT = ROOT / "reports" / "migration_signoff.md"
EVIDENCE_REPORTS = ["fault_matrix.md", "dbt_mutation_matrix.md"]

LATEST_LOADS = """SELECT TABLE_NAME, STATUS, ROWS_EXTRACTED, ROWS_LOADED, FINISHED_AT, RUN_ID
FROM PAGILA_MIG.QA.LOAD_LOG
QUALIFY ROW_NUMBER() OVER (PARTITION BY TABLE_NAME ORDER BY FINISHED_AT DESC) = 1
ORDER BY TABLE_NAME"""


@dataclass
class Trace:
    """Everything that ran for one requirement: {test name: outcomes} per suite."""

    pytest: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    dbt: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def outcomes(self) -> list[str]:
        return [o for suite in (self.pytest, self.dbt) for os_ in suite.values() for o in os_]


def git_state(report: Path) -> tuple[str, list[str]]:
    """(commit SHA, uncommitted paths other than the report itself)."""
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    report = report.resolve()
    own = report.relative_to(ROOT).as_posix() if report.is_relative_to(ROOT) else ""
    return sha, [line[3:] for line in status if line[3:] != own]


def run_dbt_tests() -> list[dict]:
    """dbt test results: name, kind (unit/data), requirements, status."""
    with tempfile.TemporaryDirectory() as tmp:
        done = subprocess.run(
            [sys.executable, "-m", "dbt.cli.main", "test", "--profiles-dir", "."]
            + ["--target-path", tmp],
            cwd=ROOT / "dbt",
            capture_output=True,
            text=True,
            check=False,
        )
        results_file = Path(tmp) / "run_results.json"
        # 0 = all passed, 1 = some tests failed; anything else means dbt itself didn't finish.
        if done.returncode not in (0, 1) or not results_file.exists():
            raise SystemExit("dbt test did not complete:\n" + done.stdout[-3000:])
        manifest = json.loads((Path(tmp) / "manifest.json").read_text())
        results = json.loads(results_file.read_text())["results"]

    nodes = {**manifest["nodes"], **manifest["unit_tests"]}
    tests = []
    for r in results:
        node = nodes[r["unique_id"]]
        declared = node["config"].get("meta", {}).get("requirement", [])
        tests.append(
            {
                "name": node["name"],
                "kind": "unit" if r["unique_id"].startswith("unit_test.") else "data",
                "requirements": [declared] if isinstance(declared, str) else declared,
                "status": "passed" if r["status"] == "pass" else r["status"],
                "message": r.get("message") or "",
            }
        )
    return tests


def latest_loads() -> list[tuple]:
    with connect() as sf:
        return sf.cursor().execute(LATEST_LOADS).fetchall()


def record_run(
    *,
    started: dt.datetime,
    sha: str,
    go: bool,
    gates: list[tuple[str, str, bool, str]],
    statuses: dict[str, str],
    waivers: dict[str, dict],
    pytest_results: list,
    dbt_results: list[dict],
) -> str:
    """Store this run in the QA schema; returns its run ID.

    SIGNOFF_RUNS is written last: each insert commits on its own, and the dashboard lists only
    runs found there, so a run never shows up with its details missing.
    """
    run_id = new_run_id()
    with connect() as sf:
        cur = sf.cursor()
        insert(cur, "SIGNOFF_GATES", [(run_id, *g) for g in gates])
        insert(
            cur,
            "SIGNOFF_REQUIREMENTS",
            (
                (run_id, r, REQUIREMENTS[r]["title"], REQUIREMENTS[r]["layer"], s, r in waivers)
                for r, s in statuses.items()
            ),
        )
        store_pytest(cur, run_id, started, pytest_results)
        store_dbt(cur, run_id, started, dbt_results)
        insert(cur, "SIGNOFF_RUNS", [(run_id, started, sha, "GO" if go else "NO-GO")])
    return run_id


def active_waiver(waivers: list[dict], req_id: str, today: dt.date) -> dict | None:
    for w in waivers:
        expires = dt.date.fromisoformat(str(w["expires"]))
        if w["requirement"] == req_id and w.get("approved_by") and expires >= today:
            return w
    return None


def one_line(message: str, limit: int = 300) -> str:
    return " ".join(message.split())[:limit]


def evidence_line(name: str) -> str:
    path = ROOT / "reports" / name
    if not path.exists():
        return f"- `reports/{name}`: not generated"
    text = path.read_text()
    generated = re.search(r"^Generated (\S+ \S+ UTC)", text, re.M)
    score = re.search(r"^\*\*(.+?)\*\*", text, re.M)
    when = generated.group(1) if generated else "unknown date"
    return f"- [`reports/{name}`]({name}): {score.group(1) if score else '?'} ({when})"


def gate(
    statuses: dict[str, str],
    traces: dict[str, Trace],
    untraced: list[str],
) -> list[tuple[str, str, bool, str]]:
    """(id, criterion, met, detail) for each gate criterion.

    untraced: tests that trace to no requirement and didn't pass, or that declare an
    unknown requirement ID; no waiver can cover them.
    """
    uncovered = [r for r, t in traces.items() if all(o == "skipped" for o in t.outcomes())]
    failing = [r for r, s in statuses.items() if s in ("FAIL", "INCOMPLETE")]
    return [
        (
            "G1",
            "Every requirement is covered by at least one test that ran",
            not uncovered,
            ", ".join(uncovered) or f"{len(traces)}/{len(traces)} covered",
        ),
        (
            "G2",
            "Every requirement passes, or has an approved, unexpired waiver",
            not failing,
            ", ".join(failing) or "no failing or incomplete requirements",
        ),
        (
            "G3",
            "Every test that traces to no requirement passes, and none declares an unknown one",
            not untraced,
            f"{len(untraced)} not passing or unknown: {', '.join(untraced[:5])}"
            if untraced
            else "all pass",
        ),
    ]


def render(
    *,
    sha: str,
    dirty: list[str],
    started: dt.datetime,
    pytest_results: list,
    dbt_results: list[dict],
    loads: list[tuple],
    traces: dict[str, Trace],
    statuses: dict[str, str],
    waivers: dict[str, dict],
    gates: list[tuple[str, str, bool, str]],
    dispositions: dict,
) -> str:
    spec = load_spec()
    columns = [c for t in spec["tables"].values() for c in t["columns"].values()]
    excluded = sum(bool(c.get("exclude")) for c in columns)
    decided = sum(d["status"] == "decided" for d in spec["decisions"].values())
    marts = sorted(p.stem for p in (ROOT / "dbt" / "models" / "marts").glob("*.sql"))
    go = all(met for _, _, met, _ in gates)

    tests = {r.test_id for r in pytest_results}
    py_failed = {r.test_id for r in pytest_results if r.outcome in ("failed", "error")}
    py_skipped = {r.test_id for r in pytest_results if r.outcome == "skipped"}
    dbt_failed = [t for t in dbt_results if t["status"] != "passed"]
    load_ok = sum(row[1] == "SUCCESS" and row[2] == row[3] for row in loads)

    lines = [
        "# Migration sign-off: Pagila → Snowflake",
        "",
        f"Generated {started:%Y-%m-%d %H:%M} UTC by `python -m reconcile.signoff` "
        f"at commit `{sha}`."
        + (
            f" The tree had {len(dirty)} uncommitted path(s), so results may not match the "
            f"commit: {', '.join(f'`{d}`' for d in dirty[:5])}."
            if dirty
            else ""
        ),
        "",
        f"## Recommendation: **{'GO' if go else 'NO-GO'}**",
        "",
        (
            "Every gate criterion is met."
            if go
            else "Not met: "
            + "; ".join(f"{g} ({detail})" for g, _, met, detail in gates if not met)
            + "."
        ),
        "",
        "| Gate | Criterion | Met | Detail |",
        "|---|---|---|---|",
        *(f"| {g} | {c} | {'yes' if met else '**no**'} | {d} |" for g, c, met, d in gates),
        "",
        "## Scope",
        "",
        f"- **Source:** PostgreSQL {spec['source']['version']}, database "
        f"`{spec['source']['database']}`, schema `{spec['source']['schema']}` (Pagila).",
        f"- **Target:** Snowflake `{spec['target']['database']}.{spec['target']['schema']}`.",
        f"- **Migrated:** {len(spec['tables'])} tables, {len(columns) - excluded} columns "
        f"({excluded} excluded by decision); {len(spec['excluded_relations'])} source views are "
        "not migrated.",
        f"- **Mapping decisions:** {decided}/{len(spec['decisions'])} decided by the human "
        "(`mapping/type_mapping.yml`).",
        f"- **Transformed:** {len(marts)} dbt marts: " + ", ".join(f"`{m}`" for m in marts) + ".",
        f"- **Requirements:** {len(REQUIREMENTS_FILE['migration'])} migration (MIG), "
        f"{len(REQUIREMENTS_FILE['etl'])} business rule (ETL); `requirements/requirements.yml`.",
        "",
        "## Run summary",
        "",
        "| Suite | Result |",
        "|---|---|",
        f"| Load (`QA.LOAD_LOG`, latest per table) | {load_ok}/{len(loads)} tables SUCCESS with "
        f"rows loaded = rows extracted; {sum(row[3] or 0 for row in loads):,} rows |",
        f"| pytest | {len(tests) - len(py_failed) - len(py_skipped)}/{len(tests)} passed"
        + (f", {len(py_failed)} failed" if py_failed else "")
        + (f", {len(py_skipped)} skipped" if py_skipped else "")
        + " |",
        f"| dbt test | {len(dbt_results) - len(dbt_failed)}/{len(dbt_results)} passed "
        f"({sum(t['kind'] == 'unit' for t in dbt_results)} unit, "
        f"{sum(t['kind'] == 'data' for t in dbt_results)} data) |",
        "",
        "## Requirement status and traceability",
        "",
        "Test names are pytest functions (with passed/total over their parameters) and dbt tests.",
        "",
        "| Requirement | Title | Status | pytest | dbt |",
        "|---|---|---|---|---|",
    ]

    def cell(suite: dict[str, list[str]]) -> str:
        return (
            "<br>".join(
                f"`{name}` {sum(o == 'passed' for o in os_)}/{len(os_)}"
                for name, os_ in sorted(suite.items())
            )
            or "·"
        )

    for req_id, trace in traces.items():
        status = statuses[req_id]
        shown = f"WAIVED ({status})" if req_id in waivers else status
        shown = shown if shown == "PASS" else f"**{shown}**"
        lines.append(
            f"| {req_id} | {REQUIREMENTS[req_id]['title']} | {shown} | {cell(trace.pytest)} "
            f"| {cell(trace.dbt)} |"
        )

    failures = [r for r in pytest_results if r.outcome in ("failed", "error")]
    if failures or dbt_failed:
        lines += ["", "## Failures", ""]
        lines += [f"- `{r.test_id}` ({r.requirement}): {one_line(r.message)}" for r in failures]
        lines += [
            f"- dbt `{t['name']}` ({', '.join(t['requirements'])}): {t['status']}, "
            f"{one_line(t['message'])}"
            for t in dbt_failed
        ]

    lines += [
        "",
        "## Known source issues",
        "",
        "Source data-quality findings that migrate faithfully, with the human disposition from "
        "`requirements/signoff.yml`. Dispositions are recorded here and don't affect the verdict.",
        "",
        "| Issue | Title | Disposition | Decided by |",
        "|---|---|---|---|",
    ]
    for src_id, issue in KNOWN_ISSUES.items():
        d = dispositions.get(src_id, {})
        lines.append(
            f"| {src_id} | {issue['title']} | {d.get('status', '**missing**')} "
            f"| {d.get('decided_by') or '·'} |"
        )

    lines += ["", "## Waivers", ""]
    lines += [
        f"- {w['requirement']}: {w['reason']} (approved by {w['approved_by']}, "
        f"expires {w['expires']})"
        for w in waivers.values()
    ] or ["None."]

    lines += [
        "",
        "## Supporting evidence",
        "",
        "Not re-run here; each report states when it was generated.",
        "",
        *(evidence_line(name) for name in EVIDENCE_REPORTS),
        "- [`AI_LOG.md`](../AI_LOG.md): defects found in AI-generated work and what caught them.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    started = dt.datetime.now(dt.UTC)
    signoff = yaml.safe_load(SIGNOFF_FILE.read_text())
    dispositions = signoff.get("dispositions") or {}
    sha, dirty = git_state(args.report)
    commit = f"{sha}-dirty" if dirty else sha

    print("running pytest ...", flush=True)
    pytest_results = run_pytest(["tests"])
    print("running dbt test ...", flush=True)
    dbt_results = run_dbt_tests()
    loads = latest_loads()

    traces = {req_id: Trace() for req_id in REQUIREMENTS}
    for r in pytest_results:
        if r.requirement:
            traces[r.requirement].pytest[r.test_id.split("::")[-1].split("[")[0]].append(r.outcome)
    # pytest rejects unknown IDs at collection; dbt meta isn't validated until here.
    unknown_ids = []
    for t in dbt_results:
        for req_id in t["requirements"]:
            if req_id in traces:
                traces[req_id].dbt[t["name"]].append(t["status"])
            else:
                unknown_ids.append(f"dbt {t['name']} (unknown {req_id})")

    today = started.date()
    statuses = {r: requirement_status(t.outcomes()) for r, t in traces.items()}
    waivers = {
        r: w
        for r, s in statuses.items()
        if s != "PASS" and (w := active_waiver(signoff.get("waivers") or [], r, today))
    }
    effective = {r: ("PASS" if r in waivers else s) for r, s in statuses.items()}
    untraced = [r.test_id for r in pytest_results if not r.requirement and r.outcome != "passed"]
    untraced += [
        f"dbt {t['name']}" for t in dbt_results if not t["requirements"] and t["status"] != "passed"
    ]
    untraced += unknown_ids
    gates = gate(effective, traces, untraced)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render(
            sha=commit,
            dirty=dirty,
            started=started,
            pytest_results=pytest_results,
            dbt_results=dbt_results,
            loads=loads,
            traces=traces,
            statuses=statuses,
            waivers=waivers,
            gates=gates,
            dispositions=dispositions,
        )
    )
    go = all(met for _, _, met, _ in gates)
    run_id = record_run(
        started=started,
        sha=commit,
        go=go,
        gates=gates,
        statuses=statuses,
        waivers=waivers,
        pytest_results=pytest_results,
        dbt_results=dbt_results,
    )
    for g, _, met, detail in gates:
        print(f"  {g} {'met' if met else 'NOT MET'}: {detail}")
    print(f"{'GO' if go else 'NO-GO'}: wrote {args.report}, stored run {run_id} in QA")
    sys.exit(0 if go else 1)


if __name__ == "__main__":
    main()
