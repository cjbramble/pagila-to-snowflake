"""Run pytest and turn its JUnit XML into per-requirement test results."""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
_REQUIREMENTS_FILE = yaml.safe_load((ROOT / "requirements" / "requirements.yml").read_text())
REQUIREMENTS = {**_REQUIREMENTS_FILE["migration"], **_REQUIREMENTS_FILE["etl"]}


@dataclass(frozen=True)
class TestResult:
    test_id: str
    requirement: str | None  # None for tests that trace to no requirement
    layer: str | None
    outcome: str  # passed, failed, error, skipped
    message: str  # failure message, empty when passed


def run_pytest(paths: list[str]) -> list[TestResult]:
    """Run pytest on paths; one result per test and requirement it covers."""
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "results.xml"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *paths,
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

    results = []
    for case in root.iter("testcase"):
        test_id = f"{case.get('classname')}::{case.get('name')}"
        outcome, message = "passed", ""
        for tag in ("failure", "error", "skipped"):
            if (element := case.find(tag)) is not None:
                outcome, message = (
                    ("failed" if tag == "failure" else tag),
                    element.get("message", ""),
                )
                break
        requirements = [
            p.get("value") for p in case.iter("property") if p.get("name") == "requirement"
        ]
        for req_id in requirements or [None]:
            layer = REQUIREMENTS[req_id]["layer"] if req_id else None
            results.append(TestResult(test_id, req_id, layer, outcome, message))
    return results
