"""Unit tests for alerts.py storage functions."""

import json

from app.alerts import load_alerts, save_alerts


class TestLoadAlerts:
    def test_returns_empty_dict_when_file_missing(self, tmp_alerts_file):
        assert not tmp_alerts_file.exists()
        result = load_alerts()
        assert result == {}

    def test_loads_valid_json(self, tmp_alerts_file):
        data = {"abc": {"keyword": "Python", "interval_minutes": 60}}
        tmp_alerts_file.write_text(json.dumps(data), encoding="utf-8")
        result = load_alerts()
        assert result == data

    def test_returns_empty_dict_on_corrupt_json(self, tmp_alerts_file):
        tmp_alerts_file.write_text("not valid json", encoding="utf-8")
        result = load_alerts()
        assert result == {}

    def test_returns_empty_dict_on_empty_file(self, tmp_alerts_file):
        tmp_alerts_file.write_text("", encoding="utf-8")
        result = load_alerts()
        assert result == {}


class TestSaveAlerts:
    def test_creates_file_with_correct_content(self, tmp_alerts_file):
        data = {"id1": {"keyword": "Django", "interval_minutes": 30}}
        save_alerts(data)
        assert tmp_alerts_file.exists()
        saved = json.loads(tmp_alerts_file.read_text(encoding="utf-8"))
        assert saved == data

    def test_roundtrip_save_and_load(self, tmp_alerts_file):
        data = {
            "alert-1": {
                "id": "alert-1",
                "keyword": "FastAPI",
                "seen_links": ["https://example.com/job/1"],
                "last_run": None,
            }
        }
        save_alerts(data)
        result = load_alerts()
        assert result == data

    def test_overwrites_existing_file(self, tmp_alerts_file):
        save_alerts({"old": {"keyword": "old"}})
        save_alerts({"new": {"keyword": "new"}})
        result = load_alerts()
        assert "old" not in result
        assert "new" in result

    def test_saves_non_ascii_content(self, tmp_alerts_file):
        data = {"id1": {"keyword": "軟體工程師"}}
        save_alerts(data)
        result = load_alerts()
        assert result["id1"]["keyword"] == "軟體工程師"
