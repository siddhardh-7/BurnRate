"""
Investigation workflow: uses the official SigNoz MCP server to gather evidence,
then asks Claude Sonnet to diagnose the root cause and estimate cost impact.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from typing import Any

import anthropic

from .prompts import SYSTEM_PROMPT

log = logging.getLogger(__name__)

_CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
_SIGNOZ_API_URL = os.getenv("SIGNOZ_API_URL", "http://localhost:3301")
_SIGNOZ_API_KEY = os.getenv("SIGNOZ_API_KEY", "")


def _build_mcp_config() -> dict[str, Any]:
    """Build MCP server config for the official SigNoz MCP server."""
    return {
        "mcpServers": {
            "signoz": {
                "command": "signoz-mcp-server",
                "env": {
                    "SIGNOZ_API_URL": _SIGNOZ_API_URL,
                    "SIGNOZ_API_KEY": _SIGNOZ_API_KEY,
                },
            }
        }
    }


async def investigate(alert: dict[str, Any]) -> dict[str, Any]:
    """
    Run the cost investigation workflow.
    1. Parse the alert for context clues (which service, what metric).
    2. Open a Claude client with SigNoz MCP server access.
    3. Have Claude autonomously query traces/metrics/logs to find the culprit.
    4. Return structured diagnosis.
    """
    alert_name = alert.get("alertname", "unknown")
    labels = alert.get("labels", {})
    service = labels.get("service_name", labels.get("job", "unknown"))
    severity = labels.get("severity", "warning")
    annotations = alert.get("annotations", {})
    description = annotations.get("description", annotations.get("summary", ""))

    log.info("Investigating alert=%r service=%r severity=%r", alert_name, service, severity)

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    investigation_prompt = f"""
A SigNoz cost alert has fired. Investigate it thoroughly.

Alert details:
- Name: {alert_name}
- Service: {service}
- Severity: {severity}
- Description: {description}
- Labels: {json.dumps(labels, indent=2)}

Using your SigNoz MCP tools:
1. Query recent burnrate.cost.usd metrics (last 30 min vs last 2 hours) to confirm the spike
2. Find which agent (burnrate.agent.id) or operation is driving the cost increase
3. Query traces for that agent/service to find abnormal patterns (retry loops, token bloat, model misroutes)
4. Check logs around the same timeframe for errors or warnings
5. Estimate the hourly cost impact if the issue continues

Return a JSON object with:
- summary: one-sentence plain-English diagnosis
- culprit_agent: agent ID or name causing the issue
- culprit_operation: the specific LLM operation
- root_cause: detailed explanation (2-3 sentences)
- evidence: list of specific data points (metric values, trace IDs, log snippets)
- estimated_hourly_cost: float, USD/hr at current burn rate
- recommended_actions: list of strings — what to do right now
- confidence: "high" | "medium" | "low"
""".strip()

    mcp_config = _build_mcp_config()

    # Write MCP config to a temp file for the SDK
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(mcp_config, f)
        config_path = f.name

    try:
        # Use Claude with SigNoz MCP tools
        # The MCP server gives Claude access to signoz_search_traces,
        # signoz_query_metrics, signoz_search_logs, signoz_list_alerts, etc.
        response = client.beta.messages.create(
            model=_CLAUDE_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": investigation_prompt}],
            mcp_servers=[
                {
                    "type": "url",
                    "url": f"{_SIGNOZ_API_URL}/api/mcp",
                    "name": "signoz",
                    "authorization_token": _SIGNOZ_API_KEY,
                }
            ],
            betas=["mcp-client-2025-04-04"],
        )
    except anthropic.BadRequestError:
        # Fallback: call SigNoz Query API directly if MCP server isn't available
        log.warning("MCP server unavailable, falling back to direct API calls")
        response = await _fallback_direct_investigation(
            client=client,
            prompt=investigation_prompt,
            service=service,
        )
        return _parse_diagnosis(response)

    # Extract the JSON diagnosis from Claude's response
    content = " ".join(
        block.text for block in response.content if hasattr(block, "text")
    )
    return _parse_diagnosis(content)


def _parse_diagnosis(content: str) -> dict[str, Any]:
    """Extract JSON from Claude's response text."""
    import re
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {
        "summary": content[:300] if content else "Investigation incomplete",
        "culprit_agent": "unknown",
        "culprit_operation": "unknown",
        "root_cause": "Could not parse structured diagnosis",
        "evidence": [],
        "estimated_hourly_cost": 0.0,
        "recommended_actions": ["Review SigNoz dashboards manually"],
        "confidence": "low",
    }


async def _fallback_direct_investigation(
    client: anthropic.Anthropic,
    prompt: str,
    service: str,
) -> str:
    """Direct Query API fallback when MCP server is unavailable."""
    import httpx

    headers = {"SIGNOZ-API-KEY": _SIGNOZ_API_KEY}
    base = _SIGNOZ_API_URL

    async with httpx.AsyncClient(timeout=10) as http:
        try:
            resp = await http.post(
                f"{base}/api/v1/query_range",
                headers=headers,
                json={
                    "start": "now-30m",
                    "end": "now",
                    "step": 60,
                    "compositeQuery": {
                        "queryType": "builder",
                        "panelType": "graph",
                        "builderQueries": {
                            "A": {
                                "dataSource": "metrics",
                                "queryName": "A",
                                "aggregateOperator": "sum",
                                "aggregateAttribute": {"key": "burnrate.cost.usd", "type": "Sum"},
                                "groupBy": [{"key": "burnrate.agent.id"}],
                                "filters": {"op": "AND", "items": []},
                            }
                        },
                    },
                },
            )
            metrics_data = resp.json() if resp.status_code == 200 else {}
        except Exception:
            metrics_data = {}

    context = f"SigNoz metrics snapshot:\n{json.dumps(metrics_data, indent=2)[:2000]}"
    msg = client.messages.create(
        model=_CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": f"{prompt}\n\nAvailable context:\n{context}"}],
    )
    return msg.content[0].text
