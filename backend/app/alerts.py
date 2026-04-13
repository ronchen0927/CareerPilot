"""
Alert storage — persists alert configurations to alerts.json.
Each alert includes: search params, notification config, seen_links, last_run.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ALERTS_FILE = Path(__file__).resolve().parent.parent / "alerts.json"

# Maximum seen_links to retain per alert (prevents unbounded growth)
MAX_SEEN_LINKS = 1000


def load_alerts() -> dict:
    """Load all alerts from disk. Returns empty dict if file doesn't exist."""
    if not ALERTS_FILE.exists():
        return {}
    try:
        return json.loads(ALERTS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to load alerts.json: %s", e)
        return {}


def save_alerts(alerts: dict) -> None:
    """Persist alerts dict to disk."""
    try:
        ALERTS_FILE.write_text(
            json.dumps(alerts, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error("Failed to save alerts.json: %s", e)
