"""Unit tests for scraper_michaelpage.py (no network calls)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import JobSearchRequest
from app.scraper_michaelpage import _build_url, _parse_date, _parse_jobs, scrape_jobs

# Trimmed from a real /zh/jobs/{keyword} response (2026-10-20)
TILE_ZH = """
<li class="views-row"><div about="/zh/job-detail/sr-bd-manager/ref/jn-082026-7086158" class="job-tile search-job-tile">
<div class="job-title " id="283801"><h3><a href="/zh/job-detail/sr-bd-manager/ref/jn-082026-7086158" rel="bookmark">Sr. Business Development Manager</a></h3></div>
<div class="job-properties"><div class="job-location"><i class="fal fa-map-marker-alt"></i> 台灣</div>
<div class="job-contract-type"><i class="far fa-clock"></i> 全職</div></div></div></li>
"""
TILE_EN = """
<li class="views-row"><div lang="en" class="job-tile search-job-tile">
<div class="job-title " id="286066"><h3><a href="/job-detail/backend-developer/ref/jn-092026-7098545?lang=zh-hant" rel="bookmark">Backend Developer (Python)</a></h3></div>
<div class="job-properties"><div class="job-location"><i class="fal fa-map-marker-alt"></i> 新北市</div></div></div></li>
"""


def _page(*tiles: str) -> str:
    return f"<html><body><ul>{''.join(tiles)}</ul></body></html>"


class TestBuildUrl:
    def test_first_page_has_no_page_param(self):
        assert _build_url("python", 1) == "https://www.michaelpage.com.tw/zh/jobs/python"

    def test_later_pages_are_zero_indexed(self):
        assert _build_url("python", 3).endswith("/zh/jobs/python?page=2")

    def test_keyword_is_path_encoded(self):
        url = _build_url("軟體工程師/後端", 1)
        assert url.endswith(
            "/zh/jobs/%E8%BB%9F%E9%AB%94%E5%B7%A5%E7%A8%8B%E5%B8%AB%2F%E5%BE%8C%E7%AB%AF"
        )

    def test_never_uses_robots_disallowed_paths(self):
        url = _build_url("python", 2)
        assert "/search/" not in url
        assert "salary" not in url and "contract" not in url


class TestParseDate:
    def test_month_year_from_ref(self):
        assert _parse_date("/job-detail/x/ref/jn-092026-7098545") == "2026/09/01"

    def test_missing_ref_returns_empty(self):
        assert _parse_date("/job-detail/x") == ""


class TestParseJobs:
    def test_parses_zh_and_en_tiles(self):
        jobs = _parse_jobs(_page(TILE_ZH, TILE_EN))
        assert [j.job for j in jobs] == [
            "Sr. Business Development Manager",
            "Backend Developer (Python)",
        ]
        assert (
            jobs[0].link
            == "https://www.michaelpage.com.tw/zh/job-detail/sr-bd-manager/ref/jn-082026-7086158"
        )
        assert jobs[1].link.endswith("?lang=zh-hant")
        assert [j.city for j in jobs] == ["台灣", "新北市"]
        assert [j.date for j in jobs] == ["2026/08/01", "2026/09/01"]
        assert all(j.source == "MichaelPage" for j in jobs)

    def test_skips_non_job_links(self):
        tile = TILE_ZH.replace("/zh/job-detail/sr-bd-manager/ref/jn-082026-7086158", "/zh/advice/x")
        assert _parse_jobs(_page(tile)) == []

    def test_empty_page(self):
        assert _parse_jobs(_page()) == []


def _mock_session(responses: list[tuple[int, str]]):
    """Build a ClientSession mock whose .get() yields the given (status, body) in order."""
    calls = []

    def get(url):
        status, body = responses[len(calls)]
        calls.append(url)
        resp = MagicMock(status=status)
        resp.text = AsyncMock(return_value=body)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=resp)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    session = MagicMock()
    session.get = get
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session, calls


class TestScrapeJobs:
    def test_stops_when_page_not_full(self):
        session, calls = _mock_session([(200, _page(TILE_ZH, TILE_EN))])
        with patch("app.scraper_michaelpage.aiohttp.ClientSession", return_value=session):
            jobs = asyncio.run(scrape_jobs(JobSearchRequest(keyword="python", pages=5)))
        assert len(jobs) == 2
        assert len(calls) == 1

    def test_stops_on_404_and_keeps_results(self):
        full_page = _page(*[TILE_ZH.replace("7086158", str(i)) for i in range(30)])
        session, calls = _mock_session([(200, full_page), (404, "")])
        with (
            patch("app.scraper_michaelpage.aiohttp.ClientSession", return_value=session),
            patch("app.scraper_michaelpage.asyncio.sleep", new=AsyncMock()),
        ):
            jobs = asyncio.run(scrape_jobs(JobSearchRequest(keyword="python", pages=5)))
        assert len(jobs) == 30
        assert calls[1].endswith("?page=1")
