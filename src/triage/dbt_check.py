"""Check proposed dbt tests without touching the project: parse and run them read-only.

Copies a dbt project to a temporary directory, overlays a proposals folder that mirrors the
project layout (models/..., tests/...), then runs dbt parse and dbt test on the 'readonly'
target (PAGILA_TRIAGE_SVC, SELECT only), so tests run against the real marts but nothing
can be built or replaced.

Usage: python -m triage.dbt_check --dbt-dir DIR --proposals DIR
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            *args,
            "--target",
            "readonly",
            "--profiles-dir",
            str(project),
            "--project-dir",
            str(project),
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dbt-dir", type=Path, required=True)
    parser.add_argument("--proposals", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "dbt"
        shutil.copytree(
            args.dbt_dir, project, ignore=shutil.ignore_patterns("target", "logs", "dbt_packages")
        )
        shutil.copytree(
            args.proposals, project, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.md")
        )

        parsed = run(project, "parse")
        if parsed.returncode != 0:
            print("dbt parse FAILED:\n" + parsed.stdout[-3000:])
            sys.exit(1)

        tested = run(project, "test")
        results_file = project / "target" / "run_results.json"
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
