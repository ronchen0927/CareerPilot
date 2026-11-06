"""Unit tests for fetchers.parse_html."""

from unittest.mock import patch

from app.fetchers import parse_html


def test_parse_html_returns_trafilatura_result():
    with patch("app.fetchers.trafilatura.extract", return_value="  Extracted content  ") as mock_t:
        result = parse_html("<html><body><p>x</p></body></html>")
    assert result == "Extracted content"
    mock_t.assert_called_once()


def test_parse_html_returns_empty_string_when_trafilatura_finds_nothing():
    with patch("app.fetchers.trafilatura.extract", return_value=None):
        result = parse_html("<html></html>")
    assert result == ""
