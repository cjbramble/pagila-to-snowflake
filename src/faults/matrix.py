"""Mutation testing for data: inject each fault, run the suite, restore, and score.

Writes reports/fault_matrix.md: which check layers caught which faults.

Usage: python -m faults.matrix [FAULT ...]
"""

import argparse
import datetime as dt
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from faults.catalog import FAULTS
from faults.inject import apply, fingerprint, restore
from migrate.snowflake_conn import connect

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports" / "fault_matrix.md"
REQUIREMENTS = yaml.safe_load((ROOT / "requirements" / "requirements.yml").read_text())["migration"]
LAYERS = ["schema", "volume", "process", "aggregate", "row", "integrity", "contract"]


def run_suite() -> dict[str, set[str]]:
    """Run the reconciliation suite; returns {layer: failed test ids}."""
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "results.xml"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/reconciliation",
                "-q",
                "-p",
                "no:cacheprovider",
                f"--junitxml={junit}",
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if not junit.exists():
            raise SystemExit("pytest produced no results; run the suite directly to see why")
        root = ET.parse(junit).getroot()

    failed: dict[str, set[str]] = {layer: set() for layer in LAYERS}
    for case in root.iter("testcase"):
        if case.find("failure") is None and case.find("error") is None:
            continue
        test_id = f"{case.get('classname')}::{case.get('name')}"
        for prop in case.iter("property"):
            if prop.get("name") == "requirement":
                failed[REQUIREMENTS[prop.get("value")]["layer"]].add(test_id)
    return failed


def render(results: list[dict], baseline_ok: bool) -> str:
    applied = [r for r in results if r["applied"]]
    detected = [r for r in applied if any(r["failed"].values())]
    score = f"{len(detected)}/{len(applied)}" + (
        f" ({100 * len(detected) / len(applied):.0f}%)" if applied else ""
    )
    lines = [
        "# Fault detection matrix",
        "",
        f"Generated {dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M} UTC by `python -m faults.matrix`. "
        f"Baseline suite before faults: {'all passed' if baseline_ok else 'FAILURES'}.",
        "",
        f"**Mutation score: {score}** faults detected by at least one layer.",
        "",
        "Cells show how many tests in that layer failed; `·` means the layer didn't notice.",
        "",
        "| Fault | Table | " + " | ".join(LAYERS) + " | Detected |",
        "|---|---|" + "---|" * len(LAYERS) + "---|",
    ]
    for r in results:
        cells = [str(len(r["failed"][layer])) if r["failed"][layer] else "·" for layer in LAYERS]
        if not r["applied"]:
            verdict = "not applied"
        else:
            verdict = "yes" if any(r["failed"].values()) else "**MISSED**"
        lines.append(f"| `{r['name']}` | {r['table']} | " + " | ".join(cells) + f" | {verdict} |")
    lines += ["", "## Faults", ""]
    lines += [f"- `{r['name']}`: {FAULTS[r['name']].description}" for r in results]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("faults", nargs="*", help="fault names (default: all)")
    args = parser.parse_args()
    if unknown := set(args.faults) - set(FAULTS):
        parser.error(f"unknown faults: {sorted(unknown)}")
    names = args.faults or list(FAULTS)

    print("baseline run ...", flush=True)
    baseline_ok = not any(run_suite().values())
    if not baseline_ok:
        raise SystemExit("baseline suite has failures; fix those before measuring faults")

    results = []
    with connect() as sf:
        for name in names:
            fault = FAULTS[name]
            before = fingerprint(sf, fault.table)
            apply(sf, fault)
            try:
                applied = fingerprint(sf, fault.table) != before
                failed = run_suite() if applied else {layer: set() for layer in LAYERS}
            finally:
                restore(sf, fault.table)
            if fingerprint(sf, fault.table) != before:
                raise SystemExit(f"{fault.table} did not restore cleanly after {name}; stopping")
            results.append(
                {"name": name, "table": fault.table, "applied": applied, "failed": failed}
            )
            caught = [layer for layer in LAYERS if failed[layer]]
            print(f"  {name:24} applied={applied} caught_by={caught or 'nothing'}", flush=True)

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(render(results, baseline_ok))
    print(f"wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
