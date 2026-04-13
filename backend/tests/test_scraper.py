"""Unit tests for scraper.py pure functions (no network calls)."""

import pytest

from app.scraper import (
    _build_url,
    _format_date,
    _format_edu,
    _format_salary,
    _parse_job,
)

# ──────────────────────────────────────────
# _format_salary
# ──────────────────────────────────────────


class TestFormatSalary:
    def test_both_zero_returns_negotiable(self):
        assert _format_salary(0, 0) == "待遇面議"

    def test_normal_range(self):
        assert _format_salary(40000, 60000) == "40,000 ~ 60,000 元"

    def test_high_cap_returns_plus_format(self):
        # 9999999 is the sentinel for "open-ended high"
        assert _format_salary(100000, 9999999) == "100,000+ 元以上"

    def test_salary_formatting_with_commas(self):
        result = _format_salary(1000000, 2000000)
        assert "1,000,000" in result
        assert "2,000,000" in result


# ──────────────────────────────────────────
# _format_date
# ──────────────────────────────────────────


class TestFormatDate:
    def test_valid_date(self):
        assert _format_date("20260223") == "2026/02/23"

    def test_empty_string_returned_as_is(self):
        assert _format_date("") == ""

    def test_wrong_length_returned_as_is(self):
        assert _format_date("2026") == "2026"
        assert _format_date("202602230000") == "202602230000"

    def test_leading_zeros_preserved(self):
        assert _format_date("20260101") == "2026/01/01"


# ──────────────────────────────────────────
# _format_edu
# ──────────────────────────────────────────


class TestFormatEdu:
    def test_empty_list_returns_no_requirement(self):
        assert _format_edu([]) == "不拘"

    def test_single_edu_level(self):
        assert _format_edu([4]) == "大學"

    def test_multiple_levels_returns_minimum(self):
        # Minimum of [3, 5] is 3 → 專科
        assert _format_edu([3, 5]) == "專科"

    def test_unknown_level_falls_back(self):
        assert _format_edu([99]) == "不拘"

    @pytest.mark.parametrize(
        "levels, expected",
        [
            ([1], "國中"),
            ([2], "高中"),
            ([3], "專科"),
            ([4], "大學"),
            ([5], "碩士"),
            ([6], "博士"),
        ],
    )
    def test_all_known_levels(self, levels, expected):
        assert _format_edu(levels) == expected


# ──────────────────────────────────────────
# _build_url
# ──────────────────────────────────────────


class TestBuildUrl:
    def test_contains_keyword(self):
        url = _build_url("Python", "", 1, "")
        assert "keyword=Python" in url

    def test_contains_page_number(self):
        url = _build_url("Python", "", 3, "")
        assert "page=3" in url

    def test_area_included_when_provided(self):
        url = _build_url("Python", "6001001000", 1, "")
        assert "area=6001001000" in url

    def test_area_omitted_when_empty(self):
        url = _build_url("Python", "", 1, "")
        assert "area=" not in url

    def test_jobexp_included_when_provided(self):
        url = _build_url("Python", "", 1, "3")
        assert "jobexp=3" in url

    def test_jobexp_omitted_when_empty(self):
        url = _build_url("Python", "", 1, "")
        assert "jobexp=" not in url


# ──────────────────────────────────────────
# _parse_job
# ──────────────────────────────────────────


class TestParseJob:
    def _make_item(self, **overrides):
        base = {
            "jobName": "軟體工程師",
            "appearDate": "20260223",
            "link": {"job": "https://www.104.com.tw/job/abc123"},
            "custName": "某某科技",
            "jobAddrNoDesc": "台北市",
            "period": 2,
            "optionEdu": [4],
            "salaryLow": 50000,
            "salaryHigh": 70000,
            "jobRo": 0,
        }
        base.update(overrides)
        return base

    def test_happy_path(self):
        job = _parse_job(self._make_item())
        assert job is not None
        assert job.job == "軟體工程師"
        assert job.company == "某某科技"
        assert job.city == "台北市"
        assert job.experience == "1-3年"
        assert job.education == "大學"
        assert job.salary_low == 50000
        assert job.salary_high == 70000
        assert job.is_featured is False

    def test_date_formatted(self):
        job = _parse_job(self._make_item(appearDate="20260101"))
        assert job.date == "2026/01/01"

    def test_missing_appear_date_uses_fallback(self):
        job = _parse_job(self._make_item(appearDate=""))
        assert job.date == "9999/12/31"

    def test_no_salary_returns_negotiable(self):
        job = _parse_job(self._make_item(salaryLow=0, salaryHigh=0))
        assert job.salary == "待遇面議"
        assert job.salary_low == 0
        assert job.salary_high == 0

    def test_featured_job_detection(self):
        # jobRo=1 and no date → featured
        job = _parse_job(self._make_item(jobRo=1, appearDate=""))
        assert job.is_featured is True

    def test_non_featured_with_date(self):
        job = _parse_job(self._make_item(jobRo=1, appearDate="20260101"))
        assert job.is_featured is False

    def test_link_extracted_from_nested_dict(self):
        job = _parse_job(self._make_item(link={"job": "https://example.com/job/xyz"}))
        assert job.link == "https://example.com/job/xyz"

    def test_invalid_link_field_returns_empty(self):
        job = _parse_job(self._make_item(link="not-a-dict"))
        assert job is not None
        assert job.link == ""

    def test_returns_none_on_fatal_error(self):
        # Pass something that can't be parsed at all
        job = _parse_job(None)  # type: ignore[arg-type]
        assert job is None
