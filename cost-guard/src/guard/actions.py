"""
Actions Cost Guard can take after diagnosing an incident.
Calls the demo-app control API to throttle or restore agents.
This closes the self-healing loop: alert → diagnose → ACT → cost drops.
"""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)

_DEMO_APP_URL = os.getenv("DEMO_APP_URL", "http://localhost:8001")


async def throttle_agent(agent_id: str, max_calls_per_minute: int = 2) -> bool:
    """Rate-limit a runaway agent. Visible immediately in the demo app's metrics."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{_DEMO_APP_URL}/control/throttle",
                params={"agent_id": agent_id, "max_calls_per_minute": max_calls_per_minute},
            )
            if resp.status_code == 200:
                log.info("ACTION: throttled agent=%s to %d calls/min", agent_id, max_calls_per_minute)
                return True
            log.warning("throttle returned %s: %s", resp.status_code, resp.text)
            return False
    except Exception as exc:
        log.warning("throttle action failed: %s", exc)
        return False


async def restore_agents() -> bool:
    """Clear all throttles once the incident is resolved."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(f"{_DEMO_APP_URL}/control/restore")
            if resp.status_code == 200:
                log.info("ACTION: all agent throttles cleared")
                return True
            return False
    except Exception as exc:
        log.warning("restore action failed: %s", exc)
        return False


async def take_action(diagnosis: dict) -> dict[str, bool]:
    """
    Decide what action to take based on the diagnosis and execute it.
    Returns a map of action_name -> success.
    """
    results: dict[str, bool] = {}
    confidence = diagnosis.get("confidence", "low")
    culprit = diagnosis.get("culprit_agent", "")
    hourly_cost = diagnosis.get("estimated_hourly_cost", 0.0)

    # Only act on high-confidence diagnoses with real cost impact
    if confidence not in ("high", "medium") or hourly_cost < 1.0:
        log.info("ACTION: skipping — confidence=%s hourly_cost=%.2f", confidence, hourly_cost)
        return results

    if culprit and culprit != "unknown":
        results["throttle"] = await throttle_agent(culprit, max_calls_per_minute=2)

    return results
