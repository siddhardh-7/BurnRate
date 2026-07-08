"""
FastAPI webhook receiver for SigNoz alerts.
SigNoz → POST /alert → Cost Guard investigation pipeline.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .investigate import investigate
from .report import build_report, send_slack

log = logging.getLogger(__name__)

_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Cost Guard webhook ready")
    yield
    log.info("Cost Guard shutting down")


app = FastAPI(title="Burnrate Cost Guard", lifespan=lifespan)


@app.post("/alert")
async def receive_alert(request: Request):
    """
    Receive a SigNoz alert webhook. SigNoz sends alerts as JSON with fields:
    alertname, state, severity, labels, generatorURL, annotations, etc.
    We extract the firing context and kick off an investigation.
    """
    if _WEBHOOK_SECRET:
        token = request.headers.get("X-Burnrate-Secret", "")
        if token != _WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="bad secret")

    body = await request.json()
    log.info("Alert received: %s state=%s", body.get("alertname"), body.get("state"))

    if body.get("state") != "firing":
        return JSONResponse({"status": "ignored", "reason": "not firing"})

    try:
        diagnosis = await investigate(alert=body)
        report = build_report(alert=body, diagnosis=diagnosis)
        await send_slack(report)
        log.info("Diagnosis complete. Cost impact: $%.4f/hr", diagnosis.get("estimated_hourly_cost", 0))
        return JSONResponse({"status": "diagnosed", "summary": diagnosis.get("summary")})
    except Exception as exc:
        log.exception("Investigation failed")
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
