from __future__ import annotations

from tessera_core.detect import (
    analyze_column,
    detect_by_content,
    detect_column,
)


# ---------- detect_column ----------


def test_exact_match_wins_with_high_confidence():
    headers = ["id", "question", "answer"]
    det = detect_column(headers, "input", ["question", "input"])
    assert det.column == "question"
    assert det.confidence == 0.95
    assert "exact match" in det.reason


def test_normalized_match_strips_prefix():
    """customer_question -> strip 'customer' prefix -> 'question' -> exact candidate hit"""
    headers = ["id", "customer_question", "answer"]
    det = detect_column(headers, "input", ["question", "input"])
    assert det.column == "customer_question"
    assert det.confidence == 0.95
    assert "normalized match" in det.reason


def test_normalized_match_strips_suffix():
    """source_text -> strip '_text' suffix -> 'source' -> exact candidate hit"""
    headers = ["id", "source_text", "answer"]
    det = detect_column(headers, "context", ["source", "policy"])
    assert det.column == "source_text"
    assert det.confidence == 0.95
    assert "normalized match" in det.reason


def test_token_match_for_compound_header():
    """Compound header that does not normalize cleanly; token match only."""
    headers = ["id", "inquiry_question_about_billing", "answer"]
    det = detect_column(headers, "input", ["question", "input"])
    assert det.column == "inquiry_question_about_billing"
    assert det.confidence == 0.85
    assert "token match" in det.reason


def test_substring_match_lowest_tier():
    headers = ["id", "userqueryfield"]
    det = detect_column(headers, "input", ["query"])
    assert det.column == "userqueryfield"
    assert det.confidence == 0.70


def test_no_match_returns_none():
    headers = ["col_a", "col_b", "col_c"]
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


# ---------- detect_by_content ----------


def test_content_fallback_picks_longest_text():
    rows = [
        {"col_a": "1", "col_b": "yes", "col_c": "this is a much longer free-text explanation"},
        {"col_a": "2", "col_b": "no", "col_c": "another long sentence describing the issue in detail"},
        {"col_a": "3", "col_b": "yes", "col_c": "a third entry with a similar amount of free-form text"},
    ]
    det = detect_by_content(rows, list(rows[0].keys()), "input", ["question"])
    assert det.column == "col_c"
    assert det.confidence == 0.40
    assert "content fallback" in det.reason


def test_content_fallback_respects_excludes():
    rows = [
        {"a": "long text " * 5, "b": "longer text " * 6, "c": "longest text " * 7},
    ]
    det = detect_by_content(
        rows, ["a", "b", "c"], "input", ["question"], exclude_columns=["c"]
    )
    assert det.column == "b"


def test_content_fallback_returns_none_when_no_text_column():
    rows = [{"a": "1", "b": "yes"}, {"a": "2", "b": "no"}]
    det = detect_by_content(rows, ["a", "b"], "input", ["question"])
    assert det.column is None
    assert det.confidence == 0.0


# ---------- analyze_column ----------


def test_analyze_column_text_type():
    rows = [
        {"q": "How do I rotate my key? It involves a bunch of steps."},
        {"q": "Why am I being rate limited even though I'm under the quota?"},
        {"q": "Where do I find the audit log for the last 30 days of activity?"},
    ]
    a = analyze_column(rows, "q")
    assert a.inferred_type == "text"
    assert a.completeness == 1.0
    assert a.distinct == 3
    assert a.avg_length > 30


def test_analyze_column_numeric_type():
    rows = [{"x": "1"}, {"x": "2"}, {"x": "3.5"}, {"x": "42"}]
    a = analyze_column(rows, "x")
    assert a.inferred_type == "numeric"
    assert a.completeness == 1.0


def test_analyze_column_category_type():
    rows = [{"label": "yes"}, {"label": "no"}, {"label": "yes"}, {"label": "no"}]
    a = analyze_column(rows, "label")
    assert a.inferred_type == "category"
    assert a.distinct == 2


def test_analyze_column_empty():
    rows = [{"q": ""}, {"q": ""}, {"q": ""}]
    a = analyze_column(rows, "q")
    assert a.inferred_type == "empty"
    assert a.completeness == 0.0
    assert a.distinct == 0
