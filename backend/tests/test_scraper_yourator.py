"""Unit tests for scraper_yourator.py pure functions (no network calls)."""

from app.scraper_yourator import _build_url, _parse_salary


class TestBuildUrl:
    def test_contains_keyword(self):
        url = _build_url("Python", 1)
        assert "term=Python" in url

    def test_contains_page(self):
        url = _build_url("Python", 3)
        assert "page=3" in url

    def test_area_mapped_to_city(self):
        url = _build_url("Python", 1, areas=["6001001000"])
        assert "location" in url
        assert "台北市" in url or "%E5%8F%B0%E5%8C%97%E5%B8%82" in url

    def test_unknown_area_skipped(self):
        url = _build_url("Python", 1, areas=["9999999999"])
        assert "location" not in url

    def test_experience_mapped(self):
        url = _build_url("Python", 1, experience=["3"])
        assert "1_3_years" in url

    def test_unknown_experience_skipped(self):
        url = _build_url("Python", 1, experience=["999"])
        assert "years_of_exp" not in url

    def test_no_filters(self):
        url = _build_url("Python", 1)
        assert "location" not in url
        assert "years_of_exp" not in url

    def test_empty_areas_list(self):
        url = _build_url("Python", 1, areas=[])
        assert "location" not in url

    def test_empty_experience_list(self):
        url = _build_url("Python", 1, experience=[])
        assert "years_of_exp" not in url

    def test_multiple_areas(self):
        url = _build_url("Python", 1, areas=["6001001000", "6001002000"])
        assert url.count("location") == 2

    def test_multiple_experience(self):
        url = _build_url("Python", 1, experience=["1", "3"])
        assert "less_than_1" in url
        assert "1_3_years" in url


class TestParseSalary:
    def test_annual_salary_converted_to_monthly(self):
        low, high, display = _parse_salary("NT$ 600,000 - 900,000 (年薪)")
        assert low == 50000
        assert high == 75000

    def test_monthly_salary_unchanged(self):
        low, high, display = _parse_salary("NT$ 50,000 (月薪)")
        assert low == 50000
        assert high == 0

    def test_negotiable(self):
        low, high, display = _parse_salary("面議")
        assert low == 0
        assert high == 0
        assert display == "待遇面議"

    def test_none_returns_negotiable(self):
        low, high, display = _parse_salary(None)
        assert display == "待遇面議"

    def test_negotiable_alternate(self):
        low, high, display = _parse_salary("待遇面議")
        assert low == 0
        assert high == 0
        assert display == "待遇面議"

    def test_single_value_monthly(self):
        low, high, display = _parse_salary("NT$ 40,000 (月薪)")
        assert low == 40000
        assert high == 0
        assert "元以上" in display

    def test_annual_salary_display_string(self):
        low, high, display = _parse_salary("NT$ 600,000 - 900,000 (年薪)")
        assert "~" in display
        assert "50,000" in display
        assert "75,000" in display
