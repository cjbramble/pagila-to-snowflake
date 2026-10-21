"""Every ETL business rule traces to at least one dbt test.

Parses the dbt project (no warehouse connection) and reads config.meta.requirement from
every data test and unit test in the manifest.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT / "dbt"
ETL_IDS = set(yaml.safe_load((ROOT / "requirements" / "requirements.yml").read_text())["etl"])


def dbt_test_requirements(tmp_path: Path) -> dict[str, set[str]]:
    """{requirement ID: names of dbt tests that declare it}."""
    # dbt parse renders the profile but never connects, so placeholders are enough.
    env = {
        "SNOWFLAKE_ACCOUNT": "parse-only",
        "SNOWFLAKE_PRIVATE_KEY_PATH": "parse-only",
        "SNOWFLAKE_TRIAGE_PRIVATE_KEY_PATH": "parse-only",
    }
    subprocess.run(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            "parse",
            "--profiles-dir",
            ".",
            "--target-path",
            str(tmp_path),
        ],
        cwd=DBT_DIR,
        env={**env, **os.environ},
        check=True,
        capture_output=True,
    )
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    tests = [n for n in manifest["nodes"].values() if n["resource_type"] == "test"]
    tests += list(manifest["unit_tests"].values())

    covered: dict[str, set[str]] = {}
    for test in tests:
        declared = test["config"].get("meta", {}).get("requirement", [])
        for req_id in [declared] if isinstance(declared, str) else declared:
            covered.setdefault(req_id, set()).add(test["name"])
    return covered


def test_every_etl_rule_has_a_dbt_test(tmp_path):
    covered = dbt_test_requirements(tmp_path)
    # ETL-008 is the mart contract requirement; Soda tests it, not dbt.
    missing = sorted(ETL_IDS - {"ETL-008"} - set(covered))
    unknown = sorted(set(covered) - ETL_IDS)
    assert not missing and not unknown, f"no dbt test: {missing}; unknown IDs in dbt: {unknown}"
