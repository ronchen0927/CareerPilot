import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from ..alerts import load_alerts, save_alerts
from ..models import AlertCreateRequest

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def list_alerts():
    """回傳所有已設定的職缺提醒（隱藏 seen_links 以減少回應大小）"""
    alerts = load_alerts()
    # Strip seen_links from the response to keep payload small
    sanitized = [{k: v for k, v in alert.items() if k != "seen_links"} for alert in alerts.values()]
    return {"alerts": sanitized}


@router.post("", status_code=201)
async def create_alert(request: AlertCreateRequest):
    """建立新的職缺提醒"""
    alerts = load_alerts()
    alert_id = str(uuid.uuid4())
    alert = {
        "id": alert_id,
        **request.model_dump(),
        "created_at": datetime.now(UTC).isoformat(),
        "last_run": None,
        "seen_links": [],
    }
    alerts[alert_id] = alert
    save_alerts(alerts)
    return {k: v for k, v in alert.items() if k != "seen_links"}


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(alert_id: str):
    """刪除職缺提醒"""
    alerts = load_alerts()
    if alert_id not in alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    del alerts[alert_id]
    save_alerts(alerts)


@router.post("/{alert_id}/trigger")
async def trigger_alert(alert_id: str):
    """立即執行一次提醒（用於測試）"""
    alerts = load_alerts()
    if alert_id not in alerts:
        raise HTTPException(status_code=404, detail="Alert not found")

    from ..scheduler import _fetch_new_jobs, _send_notification

    alert = alerts[alert_id]
    new_jobs = await _fetch_new_jobs(alert)

    if new_jobs:
        await _send_notification(alert, new_jobs)
        seen: set[str] = set(alert.get("seen_links", []))
        seen.update(j.link for j in new_jobs)
        alert["seen_links"] = list(seen)
        alert["last_run"] = datetime.now(UTC).isoformat()
        alerts[alert_id] = alert
        save_alerts(alerts)

    return {"new_jobs_found": len(new_jobs)}
