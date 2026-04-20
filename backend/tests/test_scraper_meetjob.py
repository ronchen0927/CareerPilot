"""Unit tests for scraper_meetjob.py pure functions (no network calls)."""

from app.scraper_meetjob import _build_url, _parse_city, _parse_salary


class TestBuildUrl:
    def test_contains_keyword(self):
        url = _build_url("Python", 1)
        assert "query=Python" in url

    def test_contains_location_tw(self):
        url = _build_url("Python", 1)
        assert "location=tw" in url

    def test_contains_page(self):
        url = _build_url("Python", 3)
        assert "page=3" in url

    def test_area_mapped_to_city(self):
        url = _build_url("Python", 1, areas=["6001001000"])
        assert "Taipei" in url
        assert "city" in url

    def test_unknown_area_skipped(self):
        url = _build_url("Python", 1, areas=["9999999999"])
        assert "city" not in url

    def test_experience_mapped(self):
        url = _build_url("Python", 1, experience=["3"])
        assert "1_3_years" in url

    def test_unknown_experience_skipped(self):
        url = _build_url("Python", 1, experience=["999"])
        assert "required_years" not in url

    def test_no_filters(self):
        url = _build_url("Python", 1)
        assert "city" not in url
        assert "required_years" not in url

    def test_keyword_with_spaces_encoded(self):
        url = _build_url("data engineer", 1)
        assert " " not in url

    def test_multiple_areas(self):
        url = _build_url("Python", 1, areas=["6001001000", "6001002000"])
        assert "Taipei" in url
        assert url.count("city") >= 2

    def test_multiple_experiences(self):
        url = _build_url("Python", 1, experience=["3", "5"])
        assert "1_3_years" in url
        assert "3_5_years" in url

    def test_empty_areas_list(self):
        url = _build_url("Python", 1, areas=[])
        assert "city" not in url

    def test_empty_experience_list(self):
        url = _build_url("Python", 1, experience=[])
        assert "required_years" not in url


class TestParseSalary:
    def test_annual_converted_to_monthly(self):
        low, high, _ = _parse_salary(
            {"minimum": 600000, "maximum": 900000, "paid_period_key": "annually"}
        )
        assert low == 50000
        assert high == 75000

    def test_monthly_unchanged(self):
        low, high, _ = _parse_salary(
            {"minimum": 50000, "maximum": 70000, "paid_period_key": "monthly"}
        )
        assert low == 50000
        assert high == 70000

    def test_none_returns_negotiable(self):
        low, high, display = _parse_salary(None)
        assert display == "待遇面議"

    def test_empty_dict_returns_negotiable(self):
        low, high, display = _parse_salary({})
        assert display == "待遇面議"

    def test_only_minimum_set(self):
        low, high, display = _parse_salary({"minimum": 40000, "paid_period_key": "monthly"})
        assert low == 40000
        assert high == 0
        assert "40,000" in display

    def test_zero_salary_returns_negotiable(self):
        low, high, display = _parse_salary(
            {"minimum": 0, "maximum": 0, "paid_period_key": "monthly"}
        )
        assert display == "待遇面議"


class TestParseCity:
    def test_english_city_mapped(self):
        assert _parse_city({"place": {"city": "Taipei City"}}) == "台北市"

    def test_new_taipei_city_mapped(self):
        assert _parse_city({"place": {"city": "New Taipei City"}}) == "新北市"

    def test_unknown_city_returned_as_is(self):
        result = _parse_city({"place": {"city": "Some Unknown City"}})
        assert result == "Some Unknown City"

    def test_none_returns_empty(self):
        assert _parse_city(None) == ""

    def test_missing_place_falls_back_to_handwriting_city(self):
        result = _parse_city({"handwriting_city": "Taipei City"})
        assert result == "台北市"

    def test_empty_address_returns_empty(self):
        assert _parse_city({}) == ""
