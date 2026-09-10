import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import aiohttp
import pytest

from app.models import JobSearchRequest
from app.scraper_linkedin import _build_url, _parse_jobs, scrape_jobs


def card(job_id="123", posted="2026-09-01", host="tw.linkedin.com"):
    return f'''<div class="base-search-card job-search-card">
    <a class="base-card__full-link" href="https://{host}/jobs/view/engineer-{job_id}?trackingId=x"></a>
    <h3 class="base-search-card__title">Python 工程師</h3>
    <h4 class="base-search-card__subtitle">Example</h4>
    <span class="job-search-card__location">Taipei</span>
    <time datetime="{posted}"></time></div>'''


def test_url_encoding_and_offset():
    params = parse_qs(urlsplit(_build_url("C++ 工程師 & Python", 3)).query)
    assert params["keywords"] == ["C++ 工程師 & Python"]
    assert params["start"] == ["50"]
    assert params["location"] == ["Taiwan"]


def test_parse_card_and_canonical_url():
    jobs = _parse_jobs(card())
    assert len(jobs) == 1
    job = jobs[0]
    assert (job.job, job.company, job.city) == ("Python 工程師", "Example", "Taipei")
    assert job.link == "https://www.linkedin.com/jobs/view/123"
    assert job.date == "2026/09/01"
    assert job.source == "LinkedIn"
    assert job.salary_low == 0 and job.salary == "未提供"


def test_missing_invalid_and_untrusted_cards():
    assert _parse_jobs("<html>Login required</html>") == []
    assert _parse_jobs(card(host="linkedin.com.evil.test")) == []
    assert _parse_jobs(card(job_id="invalid")) == []
    assert _parse_jobs(card(posted="invalid"))[0].date == ""
    assert _parse_jobs('<div class="base-search-card"></div>') == []


def run_scraper(responses, pages=5):
    session = MagicMock()
    session.get.side_effect = responses
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    with (
        patch("app.scraper_linkedin.aiohttp.ClientSession", return_value=cm),
        patch("app.scraper_linkedin.asyncio.sleep", new_callable=AsyncMock),
    ):
        jobs = asyncio.run(scrape_jobs(JobSearchRequest(keyword="Python", pages=pages)))
    return jobs, session.get.call_count


def response(html="", status=200):
    cm = MagicMock()
    result = MagicMock(status=status)
    result.text = AsyncMock(return_value=html)
    cm.__aenter__ = AsyncMock(return_value=result)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.parametrize(
    "failure",
    [response(status=429), response(status=302), aiohttp.ClientConnectionError(), TimeoutError()],
)
def test_partial_results_survive_failure(failure):
    jobs, calls = run_scraper([response(card()), failure])
    assert len(jobs) == 1 and calls == 2


def test_duplicate_page_stops_and_sorts():
    jobs, calls = run_scraper(
        [response(card()), response(card() + card("456", "2026-09-02")), response(card("456"))]
    )
    assert [job.date for job in jobs] == ["2026/09/02", "2026/09/01"]
    assert calls == 3


def test_page_cap():
    jobs, calls = run_scraper([response(card(str(i))) for i in range(5)], pages=20)
    assert len(jobs) == calls == 5


def test_empty_page_stops():
    jobs, calls = run_scraper([response()])
    assert jobs == [] and calls == 1


def test_search_dispatches_linkedin():
    from app.routers.jobs import search_jobs

    with patch(
        "app.routers.jobs.scrape_linkedin", new_callable=AsyncMock, return_value=_parse_jobs(card())
    ) as scraper:
        result = asyncio.run(search_jobs(JobSearchRequest(keyword="Python", sources=["linkedin"])))
    scraper.assert_awaited_once()
    assert result.count == 1 and result.results[0].source == "LinkedIn"
