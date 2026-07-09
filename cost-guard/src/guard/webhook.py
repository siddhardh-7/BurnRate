"""
FastAPI webhook receiver for SigNoz alerts.
SigNoz → POST /alert → investigate → act → report → Slack
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Must run before importing .investigate — its _MOCK_MODE (and other config) are
# module-level constants read from os.getenv() at import time, so .env has to be
# loaded into the process environment first. override=False: real shell/CI env
# vars still win over .env.
load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .actions import take_action
from .investigate import investigate
from .report import build_report, send_slack

log = logging.getLogger(__name__)

_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
_OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")


def _setup_otel_logging() -> None:
    """
    Export Cost Guard's logs to SigNoz. These log lines ARE the incident
    narrative — alert received → diagnosis → throttle action — so shipping
    them makes the whole self-healing loop visible in the SigNoz Logs view.
    Best-effort: if the OTLP endpoint is unreachable, console logging still works.
    """
    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource

        provider = LoggerProvider(resource=Resource({SERVICE_NAME: "burnrate-cost-guard"}))
        provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=_OTLP_ENDPOINT))
        )
        set_logger_provider(provider)
        logging.getLogger().addHandler(
            LoggingHandler(level=logging.INFO, logger_provider=provider)
        )
    except Exception:
        log.warning("OTel log export unavailable — console logging only", exc_info=True)


_setup_otel_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Cost Guard webhook ready — listening for SigNoz alerts")
    yield
    log.info("Cost Guard shutting down")


app = FastAPI(title="Burnrate Cost Guard", lifespan=lifespan)


@app.post("/alert")
async def receive_alert(request: Request):
    """
    Receive a SigNoz alert webhook and run the full pipeline:
      1. Investigate via SigNoz MCP server + Claude
      2. Take action (throttle culprit agent)
      3. Send Slack incident report
    """
    if _WEBHOOK_SECRET:
        token = request.headers.get("X-Burnrate-Secret", "")
        if token != _WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="bad secret")

    body = await request.json()
    # SigNoz sends "status" at the top level and also nests individual alerts under "alerts"
    # Flatten: if SigNoz batch format, extract the first alert and merge common fields
    alerts = body.get("alerts", [])
    if alerts:
        merged = {**body, **alerts[0]}
        merged.setdefault("alertname", merged.get("labels", {}).get("alertname", "unknown"))
        body = merged

    state = body.get("status") or body.get("state", "")
    log.info("Alert received: %s status=%s", body.get("alertname"), state)

    if state != "firing":
        return JSONResponse({"status": "ignored", "reason": f"state={state!r} not firing"})

    try:
        # Step 1: Investigate
        diagnosis = await investigate(alert=body)
        log.info(
            "Diagnosis: culprit=%s confidence=%s cost=%.2f/hr",
            diagnosis.get("culprit_agent"),
            diagnosis.get("confidence"),
            diagnosis.get("estimated_hourly_cost", 0),
        )

        # Step 2: Act — throttle the culprit agent if diagnosis is confident
        action_results = await take_action(diagnosis)
        if action_results:
            log.info("Actions taken: %s", action_results)
            diagnosis["actions_taken"] = action_results

        # Step 3: Report to Slack
        report = build_report(alert=body, diagnosis=diagnosis)
        await send_slack(report)

        return JSONResponse({
            "status": "diagnosed",
            "summary": diagnosis.get("summary"),
            "culprit": diagnosis.get("culprit_agent"),
            "confidence": diagnosis.get("confidence"),
            "actions_taken": action_results,
        })
    except Exception as exc:
        log.exception("Investigation failed")
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8082")))
