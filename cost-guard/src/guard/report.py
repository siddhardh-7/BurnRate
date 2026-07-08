"""Build and send incident reports."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

_SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")


def build_report(alert: dict[str, Any], diagnosis: dict[str, Any]) -> str:
    alert_name = alert.get("alertname", "Cost Alert")
    severity = alert.get("labels", {}).get("severity", "warning").upper()
    hourly = diagnosis.get("estimated_hourly_cost", 0.0)
    daily = hourly * 24

    lines = [
        f"🔥 *{alert_name}* — {severity}",
        f"*Summary:* {diagnosis.get('summary', 'N/A')}",
        f"*Culprit:* `{diagnosis.get('culprit_agent', '?')}` → `{diagnosis.get('culprit_operation', '?')}`",
        f"*Root cause:* {diagnosis.get('root_cause', 'N/A')}",
        f"*Cost impact:* ${hourly:.2f}/hr · ${daily:.2f}/day projected",
        f"*Confidence:* {diagnosis.get('confidence', 'unknown')}",
    ]

    evidence = diagnosis.get("evidence", [])
    if evidence:
        lines.append("*Evidence:*")
        for item in evidence[:5]:
            lines.append(f"  • {item}")

    # Show what Cost Guard actually did (the self-healing action)
    actions_taken = diagnosis.get("actions_taken", {})
    if actions_taken:
        lines.append("*Actions taken by Cost Guard:*")
        if actions_taken.get("throttle"):
            culprit = diagnosis.get("culprit_agent", "agent")
            lines.append(f"  ✓ Throttled `{culprit}` to 2 calls/min — burn rate will drop within 60s")

    actions = diagnosis.get("recommended_actions", [])
    if actions:
        lines.append("*Recommended next steps:*")
        for i, action in enumerate(actions, 1):
            lines.append(f"  {i}. {action}")

    return "\n".join(lines)


async def send_slack(report: str) -> None:
    if not _SLACK_WEBHOOK:
        log.info("No SLACK_WEBHOOK_URL set — printing report:\n%s", report)
        return

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            _SLACK_WEBHOOK,
            json={"text": report},
        )
        if resp.status_code != 200:
            log.warning("Slack webhook returned %s: %s", resp.status_code, resp.text)
        else:
            log.info("Slack incident report sent")
