"""
Demo App — "Patient Zero"
A multi-agent research pipeline that looks normal until chaos is injected.
Fully instrumented with OTel + burnrate-otel so costs flow to SigNoz.
"""

from __future__ import annotations

import asyncio
import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from burnrate import BurnrateSpanProcessor
from .agents.researcher import ResearchAgent
from .agents.summarizer import SummarizerAgent
from .chaos import ChaosController

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ── OTel setup ────────────────────────────────────────────────────────────────

OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
resource = Resource({SERVICE_NAME: "burnrate-demo-app"})

# MeterProvider must be set BEFORE BurnrateSpanProcessor so CostMetrics
# picks up the real provider (not the no-op default) at instantiation time.
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=OTLP_ENDPOINT), export_interval_millis=15_000
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BurnrateSpanProcessor())  # ← one line, zero config
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT)))
trace.set_tracer_provider(tracer_provider)

# Logs — the third telemetry pillar. Every Python log record (chaos activations,
# retry-loop warnings, throttle actions) is exported to SigNoz with trace context
# attached, so log lines correlate directly with the spans they occurred in.
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTLP_ENDPOINT))
)
set_logger_provider(logger_provider)
logging.getLogger().addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

# ── App ───────────────────────────────────────────────────────────────────────

chaos = ChaosController()
app = FastAPI(title="Burnrate Demo App")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "chaos_mode": chaos.active_scenario,
        "throttled_agents": chaos.throttle_state,
    }


@app.post("/research")
async def research(topic: str = "AI observability trends"):
    """Run a research + summarize pipeline. Normal cost: ~$0.02."""
    researcher = ResearchAgent(chaos=chaos)
    summarizer = SummarizerAgent(chaos=chaos)
    result = await researcher.run(topic)
    summary = await summarizer.run(result)
    return {"topic": topic, "summary": summary[:500]}


@app.post("/research/batch")
async def research_batch(count: int = 5):
    """Run multiple research tasks in parallel — useful for generating metrics volume."""
    topics = [
        "LLM cost optimization",
        "OpenTelemetry GenAI conventions",
        "AI agent architecture patterns",
        "Vector database benchmarks",
        "Prompt engineering techniques",
    ][:count]
    tasks = [asyncio.create_task(_run_pipeline(t)) for t in topics]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        "completed": sum(1 for r in results if not isinstance(r, Exception)),
        "errors": sum(1 for r in results if isinstance(r, Exception)),
    }


async def _run_pipeline(topic: str) -> str:
    researcher = ResearchAgent(chaos=chaos)
    summarizer = SummarizerAgent(chaos=chaos)
    result = await researcher.run(topic)
    return await summarizer.run(result)


# ── Chaos control (for live demo injection) ───────────────────────────────────

@app.post("/chaos/activate/{scenario}")
async def activate_chaos(scenario: str):
    """
    Activate a cost chaos scenario:
    - retry_loop: researcher retries on simulated RateLimit (8-12 attempts, cost ×10)
    - model_misroute: cheap tasks routed to expensive model (cost ×20)
    - prompt_bloat: context grows unbounded across calls (cost grows 5× per call)
    - cache_miss_storm: prompt variations defeat Anthropic caching (cache savings lost)
    """
    chaos.activate(scenario)
    log.warning("CHAOS ACTIVATED: %s", scenario)
    return {"scenario": scenario, "active": True}


@app.post("/chaos/deactivate")
async def deactivate_chaos():
    chaos.deactivate()
    return {"active": False}


@app.get("/chaos/status")
async def chaos_status():
    return {"scenario": chaos.active_scenario, "active": chaos.active_scenario is not None}


# ── Cost Guard control endpoints ──────────────────────────────────────────────
# These are called by Cost Guard's actions.py after diagnosing an incident.
# They make the self-healing loop visible: alert → diagnose → ACT → cost drops.

@app.post("/control/throttle")
async def throttle_agent(agent_id: str, max_calls_per_minute: int = 2):
    """Cost Guard calls this to rate-limit a runaway agent."""
    chaos.throttle_agent(agent_id, max_calls_per_minute)
    log.warning("THROTTLED: agent=%s max_calls_per_min=%d", agent_id, max_calls_per_minute)
    return {"throttled": agent_id, "max_calls_per_minute": max_calls_per_minute}


@app.post("/control/restore")
async def restore_agents():
    """Cost Guard calls this when the incident is resolved."""
    chaos.restore_all()
    log.info("RESTORED: all agent throttles cleared")
    return {"restored": True}


@app.get("/control/status")
async def control_status():
    return {"throttled_agents": chaos.throttle_state}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
