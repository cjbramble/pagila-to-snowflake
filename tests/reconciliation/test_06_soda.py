"""Soda data contracts on the key RAW tables (MIG-009).

Soda Core open source checks one dataset against declared rules; source-target
reconciliation is a licensed Soda feature, so the layers above do that comparison.
"""

from pathlib import Path

import pytest
from soda_core.contracts import verify_contract_locally

ROOT = Path(__file__).resolve().parents[2]
DATA_SOURCE = ROOT / "soda" / "datasources" / "snowflake.yml"
CONTRACTS = sorted((ROOT / "soda" / "contracts").glob("*.yml"))


@pytest.mark.req("MIG-009")
@pytest.mark.parametrize("contract", CONTRACTS, ids=lambda p: p.stem)
def test_soda_contract_passes(contract):
    result = verify_contract_locally(
        data_source_file_path=str(DATA_SOURCE),
        contract_file_path=str(contract),
        publish=False,
    )
    not_passed = [
        f"{c.check.column_name or 'dataset'}: {c.check.name} -> {c.outcome.name}"
        for verification in result.contract_verification_results
        for c in verification.check_results
        if c.outcome.name != "PASSED"
    ]
    assert result.is_passed and not result.has_errors, (
        f"{contract.name}: {not_passed or result.get_errors()}"
    )
