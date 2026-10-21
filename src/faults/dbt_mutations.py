"""Mutation testing for dbt models: break one business rule at a time, see which tests notice.

Each mutation is an exact text substitution in a mart model, applied to a temporary copy of
a dbt project (the repo's, or an agent's worktree). Tests run in two passes, so the report
shows what each kind of test catches:
  unit  dbt unit tests for the mutated model (mocked inputs, no data)
  data  dbt build of the mutated model plus its data and singular tests, on real data
Everything builds with the 'mutation' target into MUT_* schemas; real marts are untouched.

Usage: python -m faults.dbt_mutations [--dbt-dir DIR] [--label TEXT] [--report PATH] [NAME ...]
"""

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = Path("models") / "marts"


@dataclass(frozen=True)
class ModelMutation:
    name: str
    model: str
    rule: str
    description: str
    old: str
    new: str
    count: int = 1  # occurrences of `old` that must exist; all are replaced


MUTATIONS = [
    ModelMutation(
        "rr_floor_days",
        "mart_rental_returns",
        "ETL-006",
        "days late rounded down instead of up",
        "ceil(micros_after_due",
        "floor(micros_after_due",
        count=2,
    ),
    ModelMutation(
        "rr_datediff_seconds",
        "mart_rental_returns",
        "ETL-006",
        "lateness measured with DATEDIFF(second), which counts boundaries",
        "datediff(microsecond, due_at, return_date) as micros_after_due",
        "datediff(second, due_at, return_date) * 1000000 as micros_after_due",
    ),
    ModelMutation(
        "rr_due_exact_is_late",
        "mart_rental_returns",
        "ETL-005",
        "returned exactly at due_at counts as late",
        "when return_date <= due_at then",
        "when return_date < due_at then",
        count=2,
    ),
    ModelMutation(
        "rr_replacement_at_2x",
        "mart_rental_returns",
        "ETL-007",
        "exactly 2x overdue already charged replacement",
        "when micros_after_due > 2 * rental_duration",
        "when micros_after_due >= 2 * rental_duration",
    ),
    ModelMutation(
        "rr_replacement_plus_daily",
        "mart_rental_returns",
        "ETL-007",
        "replacement cost added to the daily fee instead of replacing it",
        "when 'replacement' then replacement_cost",
        "when 'replacement' then replacement_cost + ceil(micros_after_due / 86400000000)",
    ),
    ModelMutation(
        "rr_never_returned_none",
        "mart_rental_returns",
        "ETL-007",
        "never-returned rentals get fee basis 'none' (fee 0.00) instead of null",
        "when return_date is null then 'not_returned'\n"
        "            when return_date <= due_at then 'none'",
        "when return_date is null then 'none'\n            when return_date <= due_at then 'none'",
    ),
    ModelMutation(
        "rr_due_off_by_one",
        "mart_rental_returns",
        "ETL-004",
        "due date one day early",
        "dateadd(day, f.rental_duration,",
        "dateadd(day, f.rental_duration - 1,",
    ),
    ModelMutation(
        "rr_due_not_utc",
        "mart_rental_returns",
        "ETL-004",
        "due_at computed in Los Angeles time (same instant, non-UTC output)",
        "dateadd(day, f.rental_duration, convert_timezone('UTC', r.rental_date))",
        "dateadd(day, f.rental_duration, convert_timezone('America/Los_Angeles', r.rental_date))",
    ),
    ModelMutation(
        "rev_local_month",
        "mart_monthly_store_revenue",
        "ETL-002",
        "months bucketed in Los Angeles time instead of UTC",
        "convert_timezone('UTC', payment_date)",
        "convert_timezone('America/Los_Angeles', payment_date)",
    ),
    ModelMutation(
        "rev_staff_attribution",
        "mart_monthly_store_revenue",
        "ETL-001",
        "revenue credited by the rental's staff_id instead of the inventory's store",
        "        i.store_id\n    from",
        "        r.staff_id as store_id\n    from",
    ),
    ModelMutation(
        "rev_drop_zero_amount",
        "mart_monthly_store_revenue",
        "ETL-002",
        "zero-amount payments excluded",
        "on i.inventory_id = r.inventory_id\n)",
        "on i.inventory_id = r.inventory_id\n    where p.amount > 0\n)",
    ),
    ModelMutation(
        "rev_sum_distinct",
        "mart_monthly_store_revenue",
        "ETL-002",
        "revenue summed over distinct amounts",
        "sum(amount) as revenue",
        "sum(distinct amount) as revenue",
    ),
    ModelMutation(
        "clv_no_coalesce",
        "mart_customer_lifetime_value",
        "ETL-003",
        "customers without payments get null lifetime revenue instead of 0.00",
        "coalesce(p.lifetime_revenue, 0)::number(12, 2)",
        "p.lifetime_revenue::number(12, 2)",
    ),
    ModelMutation(
        "clv_rentals_from_payments",
        "mart_customer_lifetime_value",
        "ETL-003",
        "rental_count counts payments",
        "count(*) as rental_count\n    from {{ ref('stg_rental') }}",
        "count(*) as rental_count\n    from {{ ref('stg_payment') }}",
    ),
    ModelMutation(
        "clv_first_is_max",
        "mart_customer_lifetime_value",
        "ETL-003",
        "first_payment_at takes the latest payment",
        "convert_timezone('UTC', min(payment_date)) as first_payment_at",
        "convert_timezone('UTC', max(payment_date)) as first_payment_at",
    ),
    ModelMutation(
        "clv_inner_join",
        "mart_customer_lifetime_value",
        "ETL-003",
        "customers without payments dropped",
        "left join payments as p",
        "inner join payments as p",
    ),
]


def copy_project(dbt_dir: Path, dest: Path) -> Path:
    project = dest / "dbt"
    shutil.copytree(
        dbt_dir,
        project,
        ignore=shutil.ignore_patterns("target", "logs", "dbt_packages", ".user.yml"),
    )
    return project


def apply(project: Path, mutation: ModelMutation) -> None:
    path = project / MODELS / f"{mutation.model}.sql"
    text = path.read_text()
    found = text.count(mutation.old)
    if found != mutation.count:
        raise SystemExit(
            f"{mutation.name}: expected {mutation.count} match(es) in "
            f"{path.name}, found {found}; the model changed, update the mutation"
        )
    path.write_text(text.replace(mutation.old, mutation.new))


def dbt(project: Path, *args: str) -> list[dict]:
    """Run a dbt command on the mutation target; returns run_results entries."""
    target_path = project / "target"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            *args,
            "--target",
            "mutation",
            "--profiles-dir",
            str(project),
            "--project-dir",
            str(project),
            "--target-path",
            str(target_path),
        ],
        cwd=project,
        capture_output=True,
        check=False,
    )
    results = target_path / "run_results.json"
    return json.loads(results.read_text())["results"] if results.exists() else []


def node_name(unique_id: str) -> str:
    """Readable name from a dbt unique_id. Generic tests end in a hash, so take the part before."""
    parts = unique_id.split(".")
    return parts[2] if parts[0] == "test" and len(parts) == 4 else parts[-1]


def failures(results: list[dict], kind: str) -> list[str]:
    """Names of failed nodes of a kind: 'unit_test', 'test', or 'model'."""
    return sorted(
        node_name(r["unique_id"])
        for r in results
        if r["unique_id"].startswith(f"{kind}.") and r["status"] in ("fail", "error")
    )


def evaluate(dbt_dir: Path, names: list[str]) -> tuple[list[dict], dict]:
    with tempfile.TemporaryDirectory() as tmp:
        baseline = dbt(copy_project(dbt_dir, Path(tmp) / "baseline"), "build")
    base = {k: failures(baseline, k) for k in ("model", "unit_test", "test")}
    if not baseline or any(base.values()):
        raise SystemExit(f"baseline build is not clean: {base}; fix that before mutating")

    rows = []
    for mutation in (m for m in MUTATIONS if m.name in names):
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_project(dbt_dir, Path(tmp))
            apply(project, mutation)
            unit = dbt(project, "test", "--select", f"{mutation.model},test_type:unit")
            data = dbt(project, "build", "--select", mutation.model, "--exclude", "test_type:unit")
        row = {
            "mutation": mutation,
            "unit": failures(unit, "unit_test") + failures(unit, "model"),
            "data": failures(data, "test"),
            "stillborn": failures(data, "model"),
        }
        rows.append(row)
        verdict = (
            "stillborn"
            if row["stillborn"]
            else ("killed" if row["unit"] or row["data"] else "SURVIVED")
        )
        print(
            f"  {mutation.name:28} unit={len(row['unit'])} data={len(row['data'])} {verdict}",
            flush=True,
        )
    return rows, base


def render(rows: list[dict], label: str, dbt_dir: Path) -> str:
    valid = [r for r in rows if not r["stillborn"]]
    killed = [r for r in valid if r["unit"] or r["data"]]
    by_unit = sum(bool(r["unit"]) for r in valid)
    by_data = sum(bool(r["data"]) for r in valid)
    lines = [
        f"# dbt mutation matrix: {label}",
        "",
        f"Generated {dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M} UTC by `python -m "
        f"faults.dbt_mutations` on `{dbt_dir}`.",
        "",
        f"**Kill score: {len(killed)}/{len(valid)}** mutations caught by at least one test "
        f"(unit tests alone: {by_unit}, data tests alone: {by_data}).",
        "",
        "Cells list the failing tests; `·` means none noticed.",
        "",
        "| Mutation | Model | Rule | Unit tests | Data tests | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        m = r["mutation"]
        verdict = (
            "stillborn (didn't compile)"
            if r["stillborn"]
            else ("killed" if r["unit"] or r["data"] else "**SURVIVED**")
        )
        cell = lambda names: ", ".join(f"`{n}`" for n in names) or "·"  # noqa: E731
        lines.append(
            f"| `{m.name}` | {m.model} | {m.rule} | {cell(r['unit'])} | "
            f"{cell(r['data'])} | {verdict} |"
        )
    lines += ["", "## Mutations", ""]
    lines += [f"- `{r['mutation'].name}`: {r['mutation'].description}" for r in rows]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="mutation names (default: all)")
    parser.add_argument("--dbt-dir", type=Path, default=ROOT / "dbt")
    parser.add_argument("--label", default="existing tests")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "dbt_mutation_matrix.md")
    args = parser.parse_args()
    known = {m.name for m in MUTATIONS}
    if unknown := set(args.names) - known:
        parser.error(f"unknown mutations: {sorted(unknown)}")

    print(f"baseline build of {args.dbt_dir} ...", flush=True)
    rows, _ = evaluate(args.dbt_dir.resolve(), args.names or [m.name for m in MUTATIONS])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render(rows, args.label, args.dbt_dir))
    print(f"wrote {args.report}")


if __name__ == "__main__":
    main()
