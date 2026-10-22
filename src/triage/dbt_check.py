"""Run the project's dbt tests read-only: dbt parse, then dbt test on the 'readonly' target.

The readonly target is PAGILA_TRIAGE_SVC (SELECT only), so tests run against the real marts
but nothing can be built or replaced. dbt runs without the writable service user's key
path in its environment, so even an edited profile can't authenticate as that user.

Usage: python -m triage.dbt_check [SELECTOR ...]   (default: every test)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DBT_DIR = ROOT / "dbt"
# Credentials dbt must not see; the readonly target needs none of them.
WITHHELD_ENV = ("SNOWFLAKE_PRIVATE_KEY_PATH", "PGPASSWORD", "TRIAGE_PGPASSWORD")


def dbt_env() -> dict[str, str]:
    env = dict(os.environ)
    for name in WITHHELD_ENV:
        # Placeholders keep profile rendering working for targets that aren't used.
        env[name] = "withheld-by-dbt-check"
    return env


def run(target_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            *args,
            "--target",
            "readonly",
            "--profiles-dir",
            str(DBT_DIR),
            "--project-dir",
            str(DBT_DIR),
            "--target-path",
            str(target_path),
        ],
        cwd=DBT_DIR,
        env=dbt_env(),
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("select", nargs="*", help="dbt selectors (default: every test)")
    args = parser.parse_args()
    select = ["--select", *args.select] if args.select else []

    # A separate target path, so this never overwrites the dev target's artifacts.
    with tempfile.TemporaryDirectory() as tmp:
        target_path = Path(tmp)
        parsed = run(target_path, "parse")
        if parsed.returncode != 0:
            print("dbt parse FAILED:\n" + parsed.stdout[-3000:])
            sys.exit(1)

        tested = run(target_path, "test", *select)
        results_file = target_path / "run_results.json"
        if not results_file.exists():
            print("dbt test produced no results:\n" + tested.stdout[-3000:])
            sys.exit(1)
        results = json.loads(results_file.read_text())["results"]

    failed = [r for r in results if r["status"] != "pass"]
    for r in sorted(results, key=lambda r: r["unique_id"]):
        print(f"{r['status']:6} {r['unique_id'].split('.', 2)[-1]}")
    for r in failed:
        print(f"\n--- {r['unique_id']} ({r['status']}):\n{(r.get('message') or '').strip()[:1500]}")
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    sys.exit(1 if failed or not results else 0)


if __name__ == "__main__":
    main()
