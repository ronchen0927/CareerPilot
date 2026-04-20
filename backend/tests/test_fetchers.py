"""Unit tests for fetchers.parse_html."""

from unittest.mock import MagicMock, patch

from app.fetchers import parse_html


def test_parse_html_returns_trafilatura_result():
    with patch("app.fetchers.trafilatura.extract", return_value="  Extracted content  ") as mock_t:
        result = parse_html("<html><body><p>x</p></body></html>")
    assert result == "Extracted content"
    mock_t.assert_called_once()


def test_parse_html_falls_back_to_goose3_when_trafilatura_returns_none():
    mock_article = MagicMock()
    mock_article.cleaned_text = "Goose extracted"
    with (
        patch("app.fetchers.trafilatura.extract", return_value=None),
        patch("app.fetchers.Goose") as MockGoose,
    ):
        MockGoose.return_value.extract.return_value = mock_article
        result = parse_html("<html><body><p>x</p></body></html>")
    assert result == "Goose extracted"


def test_parse_html_returns_empty_string_when_both_fail():
    mock_article = MagicMock()
    mock_article.cleaned_text = ""
    with (
        patch("app.fetchers.trafilatura.extract", return_value=None),
        patch("app.fetchers.Goose") as MockGoose,
    ):
        MockGoose.return_value.extract.return_value = mock_article
        result = parse_html("<html></html>")
    assert result == ""


def test_parse_html_handles_goose3_exception_gracefully():
    with (
        patch("app.fetchers.trafilatura.extract", return_value=None),
        patch("app.fetchers.Goose") as MockGoose,
    ):
        MockGoose.return_value.extract.side_effect = Exception("parse error")
        result = parse_html("<html></html>")
    assert result == ""
