"""Check proposed dbt tests without touching the project: parse and run them read-only.

Copies a dbt project to a temporary directory, overlays a proposals folder that mirrors the
project layout, then runs dbt parse and dbt test on the 'readonly' target (PAGILA_TRIAGE_SVC,
SELECT only), so tests run against the real marts but nothing can be built or replaced.

Read-only holds only if a proposal can't change which credentials dbt uses, so:
  - the profile always comes from this repository's dbt/profiles.yml, never from the
    project being checked or the proposals;
  - proposals may add only test files: models/**/*.yml and tests/**/*.sql;
  - dbt runs without the writable service user's key path in its environment.

Usage: python -m triage.dbt_check --dbt-dir DIR --proposals DIR
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRUSTED_PROFILES = ROOT / "dbt" / "profiles.yml"
# Proposal files that may be overlaid: test YAML under models/, singular tests under tests/.
ALLOWED = [("models", (".yml", ".yaml")), ("tests", (".sql",))]
# Credentials dbt must not see; the readonly target needs none of them.
WITHHELD_ENV = ("SNOWFLAKE_PRIVATE_KEY_PATH", "PGPASSWORD", "TRIAGE_PGPASSWORD")


def proposal_files(proposals: Path) -> tuple[list[Path], list[Path]]:
    """(allowed, rejected) proposal files, relative to the proposals folder."""
    allowed, rejected = [], []
    for path in sorted(p for p in proposals.rglob("*") if p.is_file()):
        rel = path.relative_to(proposals)
        if rel.suffix == ".md" and len(rel.parts) == 1:
            continue  # the proposal's own README
        ok = any(rel.parts[0] == top and rel.suffix in suffixes for top, suffixes in ALLOWED)
        (allowed if ok and len(rel.parts) > 1 else rejected).append(rel)
    return allowed, rejected


def dbt_env() -> dict[str, str]:
    env = dict(os.environ)
    for name in WITHHELD_ENV:
        # Placeholders keep profile rendering working for targets that aren't used.
        env[name] = "withheld-by-dbt-check"
    return env


def run(project: Path, profiles_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            *args,
            "--target",
            "readonly",
            "--profiles-dir",
            str(profiles_dir),
            "--project-dir",
            str(project),
        ],
        cwd=project,
        env=dbt_env(),
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dbt-dir", type=Path, required=True)
    parser.add_argument("--proposals", type=Path, required=True)
    args = parser.parse_args()

    allowed, rejected = proposal_files(args.proposals)
    if rejected:
        print("rejected: proposals may only add models/**/*.yml and tests/**/*.sql:")
        print("\n".join(f"  {p}" for p in rejected))
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "dbt"
        shutil.copytree(
            args.dbt_dir,
            project,
            ignore=shutil.ignore_patterns("target", "logs", "dbt_packages", "profiles.yml"),
        )
        for rel in allowed:
            (project / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.proposals / rel, project / rel)
        profiles_dir = Path(tmp) / "profiles"
        profiles_dir.mkdir()
        shutil.copy2(TRUSTED_PROFILES, profiles_dir / "profiles.yml")

        parsed = run(project, profiles_dir, "parse")
        if parsed.returncode != 0:
            print("dbt parse FAILED:\n" + parsed.stdout[-3000:])
            sys.exit(1)

        tested = run(project, profiles_dir, "test")
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
