"""Unit tests for the AI-summary fact check; no database needed."""

from reconcile.summarize import fact_check

FAILURES = [
    (
        "MIG-003",
        "tests.reconciliation.test_02_volume::test_row_counts_match[payment]",
        "payment: source 51061, target 51058, diff -3",
    ),
    (
        "MIG-005",
        "tests.reconciliation.test_04_rows::test_row_hashes_match[payment]",
        "payment: missing 3",
    ),
]
TABLES = {"payment", "rental", "film"}


def test_accurate_summary_passes():
    summary = "MIG-003 and MIG-005 failed: payment is missing 3 rows."
    assert not any(fact_check(summary, FAILURES, TABLES).values())


def test_invented_and_omitted_items_are_flagged():
    summary = "MIG-003 and MIG-007 failed on payment and rental."
    check = fact_check(summary, FAILURES, TABLES)
    assert check["invented_requirements"] == ["MIG-007"]
    assert check["omitted_requirements"] == ["MIG-005"]
    assert check["invented_tables"] == ["rental"]


def test_numbers_must_appear_in_the_failures():
    accurate = "MIG-003 and MIG-005 failed: payment has 3 fewer rows, 51058 instead of 51061."
    wrong = "MIG-003 and MIG-005 failed: payment is missing 5 rows."
    assert fact_check(accurate, FAILURES, TABLES)["invented_numbers"] == []
    assert fact_check(wrong, FAILURES, TABLES)["invented_numbers"] == ["5"]


def test_thousands_separators_are_not_split():
    summary = "MIG-003 and MIG-005 failed: payment has 51,058 rows instead of 51,061."
    assert fact_check(summary, FAILURES, TABLES)["invented_numbers"] == []


def test_table_inside_a_column_name_is_not_a_mention():
    failures = [("MIG-007", "tests.x::test_no_orphans[payment.rental_id]", "orphaned 1 value")]
    summary = "MIG-007 failed: the rental table has orphans."
    assert fact_check(summary, failures, TABLES)["invented_tables"] == ["rental"]
