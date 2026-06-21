from __future__ import annotations

from systemsdk_core.detect import detect_column


def test_exact_match_wins_with_high_confidence():
    headers = ["id", "question", "answer"]
    det = detect_column(headers, "input", ["question", "input"])
    assert det.column == "question"
    assert det.confidence >= 0.95


def test_token_match_for_compound_header():
    headers = ["id", "customer_question", "approved_answer", "policy_context"]
    det = detect_column(headers, "input", ["question", "input"])
    assert det.column == "customer_question"
    assert 0.8 <= det.confidence < 0.95


def test_substring_match_lowest_tier():
    headers = ["id", "userqueryfield"]
    det = detect_column(headers, "input", ["query"])
    assert det.column == "userqueryfield"
    assert det.confidence == 0.70


def test_no_match_returns_none():
    headers = ["x", "y", "z"]
    det = detect_column(headers, "input", ["question", "query"])
    assert det.column is None
    assert det.confidence == 0.0


def test_override_short_circuits():
    headers = ["id", "question", "weird_field"]
    det = detect_column(headers, "input", ["question"], override="weird_field")
    assert det.column == "weird_field"
    assert det.confidence == 1.0
    assert "manual override" in det.reason


def test_override_missing_column_reports_failure():
    headers = ["id", "question"]
    det = detect_column(headers, "input", ["question"], override="not_a_column")
    assert det.column is None
    assert det.confidence == 0.0
