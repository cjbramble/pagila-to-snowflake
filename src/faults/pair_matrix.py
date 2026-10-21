"""Score a set of paired source/target checks: false alarms on clean data, then each fault.

Runs every pair in a directory (see triage.check_pair) on the clean migration, then applies
each fault in turn, re-runs the pairs, and restores the table (verified by fingerprint). A
fault that leaves the table unchanged is reported as not applied and left out of the score.
Writes a Markdown matrix of which checks caught which faults.

Usage: python -m faults.pair_matrix DIR [--label TEXT] [--report PATH] [FAULT ...]
"""

import argparse
import datetime as dt
from pathlib import Path

from faults.catalog import FAULTS
from faults.inject import apply, fingerprint, restore
from migrate.snowflake_conn import connect
from triage.check_pair import pair_names, run_pair

ROOT = Path(__file__).resolve().parents[2]


def failing(directory: Path, names: list[str]) -> list[str]:
    return [r.name for r in (run_pair(directory, n) for n in names) if not r.passed]


def render(
    label: str, directory: Path, names: list[str], clean: list[str], rows: list[dict]
) -> str:
    applied = [r for r in rows if r["applied"]]
    detected = [r for r in applied if r["failed"]]
    lines = [
        f"# Paired-check fault matrix: {label}",
        "",
        f"Generated {dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M} UTC by `python -m faults.pair_matrix` "
        f"on `{directory}` ({len(names)} checks).",
        "",
        f"**False alarms on clean data: {len(clean)}/{len(names)}**"
        + (f" ({', '.join(f'`{n}`' for n in clean)})" if clean else ""),
        "",
        f"**Faults detected: {len(detected)}/{len(applied)}** (by at least one check failing that "
        "passed on clean data; faults that changed nothing are not scored).",
        "",
        "| Fault | Table | Checks that failed |",
        "|---|---|---|",
    ]
    for r in rows:
        if not r["applied"]:
            cell = "not applied (the fault changed nothing)"
        else:
            cell = ", ".join(f"`{n}`" for n in r["failed"]) or "**none: MISSED**"
        lines.append(f"| `{r['fault']}` | {r['table']} | {cell} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", type=Path)
    parser.add_argument("faults", nargs="*", help="fault names (default: all)")
    parser.add_argument("--label", default="paired checks")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "pair_check_matrix.md")
    args = parser.parse_args()
    if unknown := set(args.faults) - set(FAULTS):
        parser.error(f"unknown faults: {sorted(unknown)}")

    names = pair_names(args.directory)
    clean = failing(args.directory, names)
    print(f"clean data: {len(clean)} false alarms {clean or ''}", flush=True)
    # A check that already fails on clean data can't show a fault, so it's left out below.
    usable = [n for n in names if n not in clean]

    rows = []
    with connect() as sf:
        for name in args.faults or list(FAULTS):
            fault = FAULTS[name]
            before = fingerprint(sf, fault.table)
            apply(sf, fault)
            try:
                applied = fingerprint(sf, fault.table) != before
                failed = failing(args.directory, usable) if applied else []
            finally:
                restore(sf, fault.table)
            if fingerprint(sf, fault.table) != before:
                raise SystemExit(f"{fault.table} did not restore cleanly after {name}; stopping")
            rows.append({"fault": name, "table": fault.table, "applied": applied, "failed": failed})
            status = f"caught_by={failed or 'nothing'}" if applied else "NOT APPLIED"
            print(f"  {name:24} {status}", flush=True)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render(args.label, args.directory, names, clean, rows))
    print(f"wrote {args.report}")


if __name__ == "__main__":
    main()
