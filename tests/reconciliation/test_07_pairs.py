"""Paired source/target checks in sql/checks/; each pair's header names its requirement."""

from pathlib import Path

import pytest

from triage import check_pair

CHECKS = Path(__file__).resolve().parents[2] / "sql" / "checks"
NAMES = check_pair.pair_names(CHECKS)


def requirement(name: str) -> str:
    return check_pair.requirement_of((CHECKS / f"{name}.pg.sql").read_text())


def pair_param(name: str):
    req = requirement(name)
    return pytest.param(name, id=name, marks=[] if req == "untagged" else [pytest.mark.req(req)])


@pytest.mark.parametrize("name", [pair_param(n) for n in NAMES])
def test_pair_results_match(pg, sf, name):
    pg_sql = check_pair.statement_of((CHECKS / f"{name}.pg.sql").read_text(), "postgres")
    sf_sql = check_pair.statement_of((CHECKS / f"{name}.sf.sql").read_text(), "snowflake")
    source = pg.execute(pg_sql).fetchall()
    target = sf.cursor().execute(sf_sql).fetchall()
    assert not (detail := check_pair.compare(source, target)), f"{name}:\n{detail}"


def test_every_pair_declares_a_requirement():
    assert not [n for n in NAMES if requirement(n) == "untagged"]
