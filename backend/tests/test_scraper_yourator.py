"""Unit tests for scraper_yourator.py pure functions (no network calls)."""

from app.scraper_yourator import _build_url, _parse_salary


class TestBuildUrl:
    def test_contains_keyword(self):
        url = _build_url("Python", 1)
        assert "Python" in url

    def test_contains_page(self):
        url = _build_url("Python", 3)
        assert "page=3" in url

    def test_area_mapped_to_yourator_code(self):
        # 6001001000 → TPE
        url = _build_url("Python", 1, areas=["6001001000"])
        assert "TPE" in url
        assert "area" in url

    def test_unknown_area_skipped(self):
        url = _build_url("Python", 1, areas=["9999999999"])
        # area[] param should not appear at all
        assert "area%5B%5D" not in url

    def test_experience_mapped(self):
        url = _build_url("Python", 1, experience=["3"])
        assert "1_3_years" in url

    def test_unknown_experience_skipped(self):
        url = _build_url("Python", 1, experience=["999"])
        assert "years_of_exp" not in url

    def test_no_filters(self):
        url = _build_url("Python", 1)
        assert "area%5B%5D" not in url
        assert "years_of_exp" not in url

    def test_empty_areas_list(self):
        url = _build_url("Python", 1, areas=[])
        assert "area%5B%5D" not in url

    def test_empty_experience_list(self):
        url = _build_url("Python", 1, experience=[])
        assert "years_of_exp" not in url

    def test_multiple_areas(self):
        url = _build_url("Python", 1, areas=["6001001000", "6001002000"])
        assert "TPE" in url
        assert "NWT" in url
        assert url.count("area%5B%5D") == 2

    def test_multiple_experience(self):
        url = _build_url("Python", 1, experience=["1", "3"])
        assert "less_than_1" in url
        assert "1_3_years" in url

    # --- category[] tests ---

    def test_category_appears_in_url(self):
        url = _build_url("Python", 1, categories=["後端工程"])
        assert "category%5B%5D" in url
        assert "%E5%BE%8C%E7%AB%AF%E5%B7%A5%E7%A8%8B" in url  # URL-encoded 後端工程

    def test_multiple_categories(self):
        url = _build_url("Python", 1, categories=["後端工程", "AI 工程師"])
        assert url.count("category%5B%5D") == 2

    def test_empty_categories_no_param(self):
        url = _build_url("Python", 1, categories=[])
        assert "category" not in url

    def test_no_categories_by_default(self):
        url = _build_url("Python", 1)
        assert "category" not in url

    # --- monthly (salary range) tests ---

    def test_monthly_both_values(self):
        url = _build_url("Python", 1, salary_min=70000, salary_max=100000)
        assert "monthly=70000%2C100000" in url or "monthly=70000,100000" in url

    def test_monthly_only_min(self):
        url = _build_url("Python", 1, salary_min=50000)
        assert "monthly" in url
        assert "50000" in url

    def test_monthly_only_max(self):
        url = _build_url("Python", 1, salary_max=80000)
        assert "monthly" in url
        assert "80000" in url

    def test_monthly_zero_not_added(self):
        url = _build_url("Python", 1, salary_min=0, salary_max=0)
        assert "monthly" not in url

    def test_monthly_not_added_by_default(self):
        url = _build_url("Python", 1)
        assert "monthly" not in url


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
