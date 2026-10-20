"""Unit tests for the row-hash diff; no database needed."""

from reconcile.rowhash import diff, number_format


def test_identical_rows_are_ok():
    rows = [("1", "a"), ("2", "b")]
    assert diff(rows, list(rows)).ok


def test_missing_extra_and_changed_are_reported_by_key():
    result = diff([("1", "a"), ("2", "b"), ("3", "c")], [("2", "b"), ("3", "X"), ("4", "d")])
    assert (result.missing, result.extra, result.changed) == (["1"], ["4"], ["3"])


def test_duplicate_target_key_is_not_collapsed():
    # A duplicated row has the same key and hash; a dict would hide it.
    result = diff([("1", "a"), ("2", "b")], [("1", "a"), ("1", "a"), ("2", "b")])
    assert not result.ok
    assert result.duplicated_target == ["1"]
    assert "duplicated in target 1: 1" in result.describe()


def test_duplicate_source_key_is_reported():
    assert diff([("1", "a"), ("1", "a")], [("1", "a")]).duplicated_source == ["1"]


def test_number_format_matches_scale():
    assert number_format("NUMBER(5,2)") == "FM990.00"
    assert number_format("NUMBER(4,2)") == "FM90.00"
    assert number_format("NUMBER(38,0)") is None
