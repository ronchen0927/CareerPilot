"""Integration tests for the /api/alerts router."""

from unittest.mock import AsyncMock, patch

from app.models import JobListing


def _make_job(**kwargs) -> JobListing:
    defaults = {
        "job": "前端工程師",
        "date": "2026/02/23",
        "link": "https://www.104.com.tw/job/abc",
        "company": "測試公司",
        "city": "台北市",
        "experience": "不拘",
        "education": "大學",
        "salary": "待遇面議",
        "salary_low": 0,
        "salary_high": 0,
    }
    defaults.update(kwargs)
    return JobListing(**defaults)


class TestListAlerts:
    def test_empty_list_initially(self, client):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        assert resp.json()["alerts"] == []

    def test_returns_created_alert(self, client, created_alert):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        assert len(resp.json()["alerts"]) == 1

    def test_seen_links_excluded_from_list(self, client, created_alert):
        resp = client.get("/api/alerts")
        for alert in resp.json()["alerts"]:
            assert "seen_links" not in alert


class TestCreateAlert:
    def test_returns_201_and_id(self, client, sample_alert_payload):
        resp = client.post("/api/alerts", json=sample_alert_payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body

    def test_returned_fields_match_input(self, client, sample_alert_payload):
        resp = client.post("/api/alerts", json=sample_alert_payload)
        body = resp.json()
        assert body["keyword"] == sample_alert_payload["keyword"]
        assert body["min_salary"] == sample_alert_payload["min_salary"]
        assert body["notify_type"] == sample_alert_payload["notify_type"]

    def test_seen_links_excluded_from_response(self, client, sample_alert_payload):
        resp = client.post("/api/alerts", json=sample_alert_payload)
        assert "seen_links" not in resp.json()

    def test_created_at_is_set(self, client, sample_alert_payload):
        resp = client.post("/api/alerts", json=sample_alert_payload)
        assert resp.json().get("created_at") is not None

    def test_last_run_is_none_initially(self, client, sample_alert_payload):
        resp = client.post("/api/alerts", json=sample_alert_payload)
        assert resp.json()["last_run"] is None

    def test_missing_keyword_returns_422(self, client, sample_alert_payload):
        payload = {**sample_alert_payload}
        del payload["keyword"]
        resp = client.post("/api/alerts", json=payload)
        assert resp.status_code == 422

    def test_missing_notify_target_returns_422(self, client, sample_alert_payload):
        payload = {**sample_alert_payload, "notify_target": ""}
        resp = client.post("/api/alerts", json=payload)
        assert resp.status_code == 422

    def test_interval_below_minimum_returns_422(self, client, sample_alert_payload):
        payload = {**sample_alert_payload, "interval_minutes": 29}
        resp = client.post("/api/alerts", json=payload)
        assert resp.status_code == 422

    def test_can_create_multiple_alerts(self, client, sample_alert_payload):
        client.post("/api/alerts", json=sample_alert_payload)
        client.post("/api/alerts", json={**sample_alert_payload, "keyword": "Django"})
        resp = client.get("/api/alerts")
        assert len(resp.json()["alerts"]) == 2


class TestDeleteAlert:
    def test_delete_existing_alert_returns_204(self, client, created_alert):
        alert_id = created_alert["id"]
        resp = client.delete(f"/api/alerts/{alert_id}")
        assert resp.status_code == 204

    def test_alert_removed_after_delete(self, client, created_alert):
        alert_id = created_alert["id"]
        client.delete(f"/api/alerts/{alert_id}")
        resp = client.get("/api/alerts")
        assert resp.json()["alerts"] == []

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/alerts/does-not-exist")
        assert resp.status_code == 404


class TestTriggerAlert:
    def test_trigger_with_no_new_jobs(self, client, created_alert):
        alert_id = created_alert["id"]
        # _fetch_new_jobs is imported from app.scheduler inside trigger_alert()
        with patch("app.scheduler._fetch_new_jobs", new=AsyncMock(return_value=[])):
            resp = client.post(f"/api/alerts/{alert_id}/trigger")
        assert resp.status_code == 200
        assert resp.json()["new_jobs_found"] == 0

    def test_trigger_with_new_jobs_calls_notification(self, client, created_alert):
        alert_id = created_alert["id"]
        jobs = [_make_job()]
        with (
            patch("app.scheduler._fetch_new_jobs", new=AsyncMock(return_value=jobs)),
            patch("app.scheduler._send_notification", new=AsyncMock()) as mock_notify,
        ):
            resp = client.post(f"/api/alerts/{alert_id}/trigger")
        assert resp.status_code == 200
        assert resp.json()["new_jobs_found"] == 1
        mock_notify.assert_called_once()

    def test_trigger_nonexistent_returns_404(self, client):
        resp = client.post("/api/alerts/does-not-exist/trigger")
        assert resp.status_code == 404
