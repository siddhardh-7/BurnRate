"""
Investigation workflow: spawns the official SigNoz MCP server (stdio transport),
connects via the MCP Python SDK, then runs a Claude tool-use loop to diagnose
the root cause of the cost incident.

Why stdio instead of the Anthropic URL-based MCP beta:
  The SigNoz MCP server is a local binary, not a hosted HTTP endpoint. Using the
  MCP Python package gives us a stable, testable connection that works identically
  locally, in Docker, and on EC2 — no dependency on SigNoz Cloud exposing /api/mcp.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

from .prompts import SYSTEM_PROMPT

log = logging.getLogger(__name__)

_CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
_SIGNOZ_API_URL = os.getenv("SIGNOZ_API_URL", "http://localhost:8080")
_SIGNOZ_API_KEY = os.getenv("SIGNOZ_API_KEY", "")
# SigNoz ships MCP at /mcp on port 8000 when enabled via casting.yaml
_SIGNOZ_MCP_URL = os.getenv("SIGNOZ_MCP_URL", "http://localhost:8000/mcp")
_MAX_TOOL_ROUNDS = 8


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


_MOCK_MODE = _env_bool("COST_GUARD_MOCK", True)  # set COST_GUARD_MOCK=false in .env after adding Anthropic credits


async def investigate(alert: dict[str, Any]) -> dict[str, Any]:
    alert_name = alert.get("alertname", "unknown")
    labels = alert.get("labels", {})
    service = labels.get("service_name", labels.get("job", "unknown"))
    severity = labels.get("severity", "warning")
    annotations = alert.get("annotations", {})
    description = annotations.get("description", annotations.get("summary", ""))

    log.info("Investigating alert=%r service=%r severity=%r", alert_name, service, severity)

    if _MOCK_MODE:
        log.info("MOCK MODE: returning synthetic diagnosis (set COST_GUARD_MOCK=false to use real LLM)")
        return _mock_diagnosis(service, description)

    prompt = _build_prompt(alert_name, service, severity, description, labels)

    try:
        return await _investigate_via_mcp(prompt)
    except Exception as exc:
        log.warning("MCP investigation failed (%s), falling back to direct API", exc)
        return await _investigate_direct(prompt, service)


def _mock_diagnosis(service: str, description: str) -> dict[str, Any]:
    """
    Realistic synthetic diagnosis for demo/testing when Anthropic credits are unavailable.
    Simulates what the real LLM investigation would return for a retry_loop chaos scenario.
    """
    import time
    return {
        "summary": "researcher-v1 is stuck in a retry loop causing 8-10x cost spike on burnrate-demo-app",
        "culprit_agent": "researcher-v1",
        "culprit_operation": "gen_ai chat",
        "root_cause": (
            "SigNoz traces show researcher-v1 making 8-12 LLM calls per research task "
            "instead of 1. Each failed attempt logs a RateLimitError. Input tokens grew "
            "from ~170 (baseline) to ~1,400 per task due to accumulated retry context. "
            "Burn rate jumped from $0.0003/min to $0.0028/min — a 9.3x spike."
        ),
        "evidence": [
            "burnrate.cost.usd rate: 0.000047/s → 0.000183/s (3.9x above threshold)",
            "researcher-v1 span count: 47 spans in 15min vs 5 baseline (9.4x normal)",
            "gen_ai.usage.input_tokens p95: 1,387 tokens vs 171 baseline",
            "demo.simulated_failure=true on 8 of 10 spans — retry loop confirmed",
            "Chaos scenario: retry_loop active on burnrate-demo-app",
        ],
        "estimated_hourly_cost": 10.98,
        "recommended_actions": [
            "Throttle researcher-v1 to 2 calls/minute immediately",
            "Check retry backoff logic — exponential backoff missing",
            "Add per-agent hourly budget cap of $2.00",
        ],
        "confidence": "high",
        "_mock": True,
    }


# ── MCP-based investigation ───────────────────────────────────────────────────

async def _investigate_via_mcp(prompt: str) -> dict[str, Any]:
    """
    Connects to SigNoz's built-in MCP server (HTTP transport, port 8000).
    Runs a Claude tool-use loop: Claude calls MCP tools → we execute them →
    feed results back → repeat until Claude returns a JSON diagnosis.
    """
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError:
        raise RuntimeError("mcp package not installed — run: pip install mcp")

    headers = {"SIGNOZ-API-KEY": _SIGNOZ_API_KEY} if _SIGNOZ_API_KEY else {}
    log.info("Connecting to SigNoz MCP at %s", _SIGNOZ_MCP_URL)

    async with streamablehttp_client(_SIGNOZ_MCP_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            log.info("SigNoz MCP: %d tools available", len(tools_response.tools))
            # Keep only the tools needed for cost investigation — 41 tools exceeds token limits
            _RELEVANT_TOOLS = {
                "signoz_search_traces", "signoz_get_trace", "signoz_query_metrics",
                "signoz_get_services", "signoz_get_operations", "signoz_query_logs",
                "signoz_get_exceptions", "signoz_list_dashboards",
            }
            claude_tools = [
                _mcp_tool_to_claude(t) for t in tools_response.tools
                if t.name in _RELEVANT_TOOLS
            ]
            log.info("Filtered to %d investigation tools", len(claude_tools))

            client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            messages: list[dict] = [{"role": "user", "content": prompt}]

            for round_num in range(_MAX_TOOL_ROUNDS):
                response = await client.messages.create(
                    model=_CLAUDE_MODEL,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=claude_tools,
                    messages=messages,
                )

                log.info("MCP round %d: stop_reason=%s", round_num + 1, response.stop_reason)

                if response.stop_reason == "end_turn":
                    text = " ".join(
                        b.text for b in response.content if hasattr(b, "text")
                    )
                    return _parse_diagnosis(text)

                tool_uses = [b for b in response.content if b.type == "tool_use"]
                if not tool_uses:
                    text = " ".join(
                        b.text for b in response.content if hasattr(b, "text")
                    )
                    return _parse_diagnosis(text)

                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for tu in tool_uses:
                    log.info("[SigNoz MCP] calling tool: %s", tu.name)
                    try:
                        mcp_result = await session.call_tool(tu.name, tu.input)
                        content = _mcp_content_to_str(mcp_result.content)
                    except Exception as exc:
                        content = f"Tool error: {exc}"
                        log.warning("MCP tool %s failed: %s", tu.name, exc)

                    # Truncate large tool results to stay under rate limits
                    if len(content) > 2000:
                        content = content[:2000] + "\n... [truncated]"
                    log.info("[SigNoz MCP] %s → %s", tu.name, content[:200])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": content,
                    })

                messages.append({"role": "user", "content": tool_results})

            # Exhausted rounds — ask Claude to synthesize from what it has
            messages.append({
                "role": "user",
                "content": "You have reached the investigation limit. Synthesize what you found into the JSON diagnosis format now.",
            })
            final = await client.messages.create(
                model=_CLAUDE_MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            text = " ".join(b.text for b in final.content if hasattr(b, "text"))
            return _parse_diagnosis(text)


def _mcp_tool_to_claude(tool: Any) -> dict:
    """Convert an MCP tool definition to Anthropic tool_use format."""
    schema = {}
    if hasattr(tool, "inputSchema") and tool.inputSchema:
        schema = tool.inputSchema if isinstance(tool.inputSchema, dict) else {}
    return {
        "name": tool.name,
        "description": getattr(tool, "description", ""),
        "input_schema": schema or {"type": "object", "properties": {}},
    }


def _mcp_content_to_str(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif isinstance(item, dict):
                parts.append(json.dumps(item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


# ── Direct API fallback ───────────────────────────────────────────────────────

async def _investigate_direct(prompt: str, service: str) -> dict[str, Any]:
    """
    Fallback when MCP binary is unavailable: fetch raw metrics from SigNoz
    Query API and ask Claude to diagnose from the data directly.
    """
    import httpx

    headers = {"SIGNOZ-API-KEY": _SIGNOZ_API_KEY}
    metrics_snapshot = ""

    async with httpx.AsyncClient(timeout=10) as http:
        try:
            resp = await http.post(
                f"{_SIGNOZ_API_URL}/api/v3/query_range",
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
                                "aggregateOperator": "rate",
                                "aggregateAttribute": {
                                    "key": "burnrate.cost.usd",
                                    "type": "Sum",
                                },
                                "groupBy": [{"key": "burnrate.agent.id"}],
                                "filters": {"op": "AND", "items": []},
                            }
                        },
                    },
                },
            )
            if resp.status_code == 200:
                metrics_snapshot = json.dumps(resp.json(), indent=2)[:3000]
        except Exception as exc:
            log.warning("Direct metric fetch failed: %s", exc)

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    context = f"SigNoz metrics (last 30 min):\n{metrics_snapshot}" if metrics_snapshot else "No metrics available."
    msg = await client.messages.create(
        model=_CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"{prompt}\n\n{context}"}],
    )
    return _parse_diagnosis(msg.content[0].text)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_prompt(
    alert_name: str,
    service: str,
    severity: str,
    description: str,
    labels: dict,
) -> str:
    return f"""
A SigNoz cost alert has fired. Investigate it using the playbook in your system prompt.

Alert:
  name: {alert_name}
  service: {service}
  severity: {severity}
  description: {description}
  labels: {json.dumps(labels)}

Follow the 5-step investigation playbook. Call SigNoz MCP tools to get real data.
Return only a JSON diagnosis — no prose outside the JSON object.
""".strip()


def _parse_diagnosis(content: str) -> dict[str, Any]:
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
        "root_cause": "Could not parse structured diagnosis from Claude response.",
        "evidence": [],
        "estimated_hourly_cost": 0.0,
        "recommended_actions": ["Review SigNoz dashboards manually"],
        "confidence": "low",
    }
