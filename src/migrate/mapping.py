"""Load the Postgres → Snowflake mapping spec."""

from pathlib import Path
from typing import Any

import yaml

SPEC_PATH = Path(__file__).resolve().parents[2] / "mapping" / "type_mapping.yml"


def load_spec(path: Path = SPEC_PATH) -> dict[str, Any]:
    """Parse the mapping spec YAML."""
    return yaml.safe_load(path.read_text())
