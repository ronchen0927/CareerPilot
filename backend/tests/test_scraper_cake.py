"""Unit tests for scraper_cake.py pure functions (no network calls)."""

from unittest.mock import patch

from app.models import JobSearchRequest
from app.scraper_cake import (
    MAX_PAGES,
    _build_url,
    _extract_jobs_from_next_data,
    _parse_city,
    _parse_date,
    _parse_job,
    _parse_salary,
    scrape_jobs,
)


class TestBuildUrl:
    def test_contains_keyword(self):
        url = _build_url("Python", 1)
        # Keyword should be in the URL path, not as a query param
        assert "/jobs/Python" in url
        assert "q=" not in url

    def test_contains_page(self):
        url = _build_url("Python", 3)
        assert "page=3" in url

    def test_contains_locale(self):
        url = _build_url("Python", 1)
        assert "locale=zh-TW" in url

    def test_base_url(self):
        url = _build_url("Python", 1)
        assert url.startswith("https://www.cake.me/jobs/Python")

    def test_area_codes_mapped_to_city_slug(self):
        url = _build_url("Python", 1, areas=["6001001000"])
        # Location value should be Chinese: 台北市-台灣 (URL-encoded)
        assert "%E5%8F%B0%E5%8C%97%E5%B8%82" in url  # 台北市

    def test_experience_codes_mapped(self):
        url = _build_url("Python", 1, experience=["3"])
        assert "seniority_levels" in url
        assert "junior" in url

    def test_unknown_area_skipped(self):
        url = _build_url("Python", 1, areas=["9999999999"])
        assert "locations" not in url

    def test_keyword_is_urlencoded(self):
        url = _build_url("軟體工程師", 1)
        # Chinese keyword should appear URL-encoded in the path
        assert "%E8%BB%9F%E9%AB%94" in url  # 軟體
        assert "軟體工程師" not in url  # raw unencoded form must not appear

    def test_empty_areas_adds_no_city_param(self):
        url = _build_url("Python", 1, areas=[])
        assert "locations" not in url

    def test_empty_experience_adds_no_exp_param(self):
        url = _build_url("Python", 1, experience=[])
        assert "seniority_levels" not in url

    def test_multiple_areas_all_mapped(self):
        url = _build_url("Python", 1, areas=["6001001000", "6001002000"])
        assert "%E5%8F%B0%E5%8C%97%E5%B8%82" in url  # 台北市
        assert "%E6%96%B0%E5%8C%97%E5%B8%82" in url  # 新北市


class TestPagesCappedAtMax:
    def test_pages_capped_at_max(self):
        """scrape_jobs should fetch at most MAX_PAGES pages even if request.pages is larger."""
        import asyncio
        from unittest.mock import AsyncMock

        call_count = 0

        async def fake_fetch_page(page, url):
            nonlocal call_count
            call_count += 1
            return []

        async def run():
            request = JobSearchRequest(keyword="Python", pages=MAX_PAGES + 5)

            mock_playwright = AsyncMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_playwright.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            mock_playwright_cm = AsyncMock()
            mock_playwright_cm.__aenter__.return_value = mock_playwright

            with patch("app.scraper_cake._fetch_page", side_effect=fake_fetch_page):
                with patch("app.scraper_cake.async_playwright", return_value=mock_playwright_cm):
                    await scrape_jobs(request)

        asyncio.run(run())
        assert call_count == MAX_PAGES


class TestParseDate:
    def test_iso_datetime(self):
        assert _parse_date("2026-04-10T12:00:00.000Z") == "2026/04/10"

    def test_date_only(self):
        assert _parse_date("2026-04-10") == "2026/04/10"

    def test_empty_returns_fallback(self):
        assert _parse_date("") == "9999/12/31"

    def test_none_returns_fallback(self):
        assert _parse_date(None) == "9999/12/31"


class TestParseSalary:
    def test_both_none_returns_negotiable(self):
        low, high, text = _parse_salary({"min": None, "max": None, "type": "per_month"})
        assert low == 0 and high == 0 and text == "待遇面議"

    def test_empty_dict_returns_negotiable(self):
        low, high, text = _parse_salary({})
        assert text == "待遇面議"

    def test_none_returns_negotiable(self):
        low, high, text = _parse_salary(None)
        assert text == "待遇面議"

    def test_monthly_range(self):
        low, high, text = _parse_salary({"min": "40000", "max": "60000", "type": "per_month"})
        assert low == 40000 and high == 60000
        assert "40,000" in text and "60,000" in text

    def test_annual_converted_to_monthly(self):
        low, high, text = _parse_salary({"min": "600000", "max": "1200000", "type": "per_year"})
        assert low == 50000 and high == 100000

    def test_min_only(self):
        low, high, text = _parse_salary({"min": "50000", "max": None, "type": "per_month"})
        assert low == 50000 and high == 0
        assert "以上" in text


class TestParseCity:
    def test_zh_tw_locale_preferred(self):
        entity = {
            "locationsWithLocale": [{"zh-TW": "台北市", "en": "Taipei"}],
            "locations": ["Taipei"],
        }
        assert _parse_city(entity) == "台北市"

    def test_fallback_to_locations(self):
        entity = {
            "locationsWithLocale": [{"en": "Taipei"}],
            "locations": ["台灣"],
        }
        assert _parse_city(entity) == "台灣"

    def test_empty_returns_empty(self):
        assert _parse_city({}) == ""


class TestExtractJobsFromNextData:
    def _make_data(self, paths: list[str], entities: dict) -> dict:
        return {
            "props": {
                "pageProps": {
                    "initialState": {
                        "jobSearch": {
                            "viewsByFilterKey": {
                                '{"filters":{}}': {
                                    "pageMap": {"1": paths},
                                    "pagination": {"current_page": 1},
                                }
                            },
                            "entityByPathId": entities,
                        }
                    }
                }
            }
        }

    def test_returns_entities_in_order(self):
        data = self._make_data(
            ["path-a", "path-b"],
            {"path-a": {"title": "Job A"}, "path-b": {"title": "Job B"}},
        )
        result = _extract_jobs_from_next_data(data)
        assert len(result) == 2
        assert result[0]["title"] == "Job A"
        assert result[1]["title"] == "Job B"

    def test_missing_path_skipped(self):
        data = self._make_data(["path-a", "missing"], {"path-a": {"title": "Job A"}})
        result = _extract_jobs_from_next_data(data)
        assert len(result) == 1

    def test_empty_structure_returns_empty(self):
        assert _extract_jobs_from_next_data({}) == []

    def test_no_views_returns_empty(self):
        data = {"props": {"pageProps": {"initialState": {"jobSearch": {"viewsByFilterKey": {}}}}}}
        assert _extract_jobs_from_next_data(data) == []


class TestParseJob:
    def _make_entity(self, **overrides) -> dict:
        base = {
            "path": "backend-engineer-abc123",
            "title": "後端工程師",
            "page": {"name": "某科技公司"},
            "locationsWithLocale": [{"zh-TW": "台北市"}],
            "locations": ["台北市"],
            "contentUpdatedAt": "2026-04-10T00:00:00.000Z",
            "seniorityLevel": "junior",
            "salary": {"min": "50000", "max": "80000", "type": "per_month"},
        }
        base.update(overrides)
        return base

    def test_happy_path(self):
        job = _parse_job(self._make_entity())
        assert job is not None
        assert job.job == "後端工程師"
        assert job.company == "某科技公司"
        assert job.source == "CakeResume"
        assert job.link == "https://www.cake.me/jobs/backend-engineer-abc123"
        assert job.date == "2026/04/10"
        assert job.city == "台北市"
        assert job.experience == "1-3年"
        assert job.is_featured is False

    def test_no_salary_returns_negotiable(self):
        job = _parse_job(self._make_entity(salary={"min": None, "max": None, "type": "per_month"}))
        assert job is not None
        assert job.salary == "待遇面議"
        assert job.salary_low == 0
        assert job.salary_high == 0

    def test_source_is_cakeresume(self):
        job = _parse_job(self._make_entity())
        assert job is not None
        assert job.source == "CakeResume"

    def test_education_defaults_to_no_restriction(self):
        job = _parse_job(self._make_entity())
        assert job is not None
        assert job.education == "不拘"

    def test_returns_none_on_fatal_error(self):
        # Passing None should be caught and return None
        assert _parse_job(None) is None  # type: ignore[arg-type]

    def test_unknown_seniority_level_used_as_is(self):
        job = _parse_job(self._make_entity(seniorityLevel="no_preference"))
        assert job is not None
        assert job.experience == "不拘"
