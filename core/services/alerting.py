"""
QA-25: External alerting hook.

Provides a simple, extensible alerting mechanism.
- Always logs to Python logger (default)
- Optionally sends to webhook URL (Slack, Discord, Sentry, etc.)
- Configure via ALERT_WEBHOOK_URL env var

Usage:
    from core.services.alerting import send_alert
    send_alert("Job stuck", severity="warning", context={"job_id": "abc"})
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Severity levels
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
SEVERITY_CRITICAL = "critical"


def send_alert(
    message: str,
    severity: str = SEVERITY_WARNING,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send an alert through configured channels.

    Args:
        message: Human-readable alert message
        severity: info | warning | error | critical
        context: Optional dict with structured data (job_id, user_id, etc.)

    Returns:
        True if alert was sent successfully to all channels
    """
    payload = {
        "timestamp": datetime.now().isoformat(),
        "severity": severity,
        "message": message,
        "context": context or {},
        "service": "ai-publisher-pro",
    }

    # 1. Always log locally
    log_fn = {
        SEVERITY_INFO: logger.info,
        SEVERITY_WARNING: logger.warning,
        SEVERITY_ERROR: logger.error,
        SEVERITY_CRITICAL: logger.critical,
    }.get(severity, logger.warning)

    log_fn(f"ALERT [{severity.upper()}]: {message} | ctx={context}")

    # 2. Webhook (Slack / Discord / custom)
    webhook_url = os.getenv("ALERT_WEBHOOK_URL", "")
    if webhook_url:
        try:
            import httpx

            # Format as Slack-compatible payload
            slack_payload = {
                "text": f"*[{severity.upper()}]* {message}",
                "attachments": [
                    {
                        "color": {
                            SEVERITY_INFO: "#36a64f",
                            SEVERITY_WARNING: "#ffcc00",
                            SEVERITY_ERROR: "#ff6600",
                            SEVERITY_CRITICAL: "#ff0000",
                        }.get(severity, "#cccccc"),
                        "fields": [
                            {"title": k, "value": str(v), "short": True}
                            for k, v in (context or {}).items()
                        ],
                        "ts": datetime.now().timestamp(),
                    }
                ],
            }

            with httpx.Client(timeout=5.0) as client:
                resp = client.post(webhook_url, json=slack_payload)
                if resp.status_code != 200:
                    logger.warning(f"Webhook returned {resp.status_code}")
                    return False
        except ImportError:
            logger.debug("httpx not installed, webhook alerting skipped")
        except Exception as e:
            logger.warning(f"Webhook alert failed: {e}")
            return False

    return True
