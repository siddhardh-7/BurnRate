# Burnrate — Setup & Deployment Guide

Complete walkthrough for judges and anyone deploying the Burnrate project locally.

## Table of Contents

1. [Quick Start](#quick-start) — Get everything running in under 5 minutes
2. [Prerequisites](#prerequisites) — What you need installed
3. [Architecture Overview](#architecture-overview) — How the pieces fit together
4. [Demo Walkthrough](#demo-walkthrough) — Step-by-step chaos injection & recovery
5. [Dashboards & Alerts](#dashboards--alerts) — Where to watch the action
6. [Troubleshooting](#troubleshooting) — Common issues & fixes
7. [Cleanup](#cleanup) — Tear down safely

---

## Quick Start

Two commands start the full stack: SigNoz first, then the Burnrate services.

### 1. Clone the repository

```bash
git clone https://github.com/siddhardh-7/BurnRate.git
cd BurnRate
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env — at minimum, fill in ANTHROPIC_API_KEY (or leave COST_GUARD_MOCK=true)
```

The defaults in `.env.example` work out of the box. The only key you need for real LLM investigations is `ANTHROPIC_API_KEY`. Without it, Cost Guard runs in mock mode (full E2E loop, synthetic diagnosis).

### 3. Install and start SigNoz via Foundry

```bash
# Install foundryctl (if not already installed)
curl -sL https://dl.signoz.io/foundryctl/install.sh | bash

# Cast reads casting.yaml + casting.yaml.lock from the repo root and starts SigNoz
foundryctl cast
```

This starts SigNoz (UI, OTel ingester, MCP server, ClickHouse, PostgreSQL) from the pinned configuration in this repo. Should take ~60–90 seconds.

Wait for SigNoz to be ready — visit **http://localhost:8080**.

> **Tip**: Watch startup progress with `docker compose -f pours/deployment/compose.yaml logs -f signoz-signoz-0`

### 4. Start Burnrate services

```bash
docker-compose up --build
```

**Wait for both containers to become healthy:**
- `burnrate-demo-app`: Ready on port 8001
- `burnrate-cost-guard`: Webhook listening on port 8082

Expected startup time: **20–30 seconds** (after SigNoz is already up).

### 5. Run a demo scenario

In a separate terminal:

```bash
# Inject a retry loop on researcher-v1
curl -X POST http://localhost:8001/chaos/activate/retry_loop

# Generate traffic to trigger the failure
curl -X POST "http://localhost:8001/research/batch?count=5"

# Watch the logs:
docker logs -f burnrate-demo-app
docker logs -f burnrate-cost-guard
```

Then open **http://localhost:8080** and watch:
- **SigNoz Metrics** → `burnrate.cost.usd` climbs in real time
- **Alert fires** → BurnRateBudgetAlert triggered
- **Cost Guard logs** → Investigates via SigNoz MCP, diagnoses, throttles
- **Cost recovers** → researcher-v1 throttled, spend drops to baseline

### 6. Restore and reset

```bash
curl -X POST http://localhost:8001/chaos/deactivate
curl -X POST http://localhost:8001/control/restore
```

---

## Prerequisites

### Required

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
  - Check: `docker --version && docker compose version`
- **foundryctl** — SigNoz deployment tool
  - Install: `curl -sL https://dl.signoz.io/foundryctl/install.sh | bash`
  - Check: `foundryctl version`
- **Curl** or a REST client (for chaos injection)

### Optional

- **Anthropic API key** — for real Cost Guard investigations. Without it, mock mode runs the full loop with a synthetic diagnosis. Get one at https://console.anthropic.com

### System Requirements

| Component | CPU | Memory | Disk |
|-----------|-----|--------|------|
| SigNoz stack | 2 cores | 2GB | 1GB |
| Demo App | 0.5 core | 256MB | 50MB |
| Cost Guard | 0.5 core | 256MB | 50MB |
| **Total** | **~3 cores** | **~2.5GB** | **~1.1GB** |

Docker Desktop users: set **Memory ≥ 4GB** in Preferences → Resources.

---

## Architecture Overview

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                           BURNRATE LOOP                              │
└─────────────────────────────────────────────────────────────────────┘

  1. AGENTS                   2. SPANS                  3. ENRICHMENT
  ┌─────────────────┐        ┌──────────────────┐      ┌──────────────┐
  │ researcher-v1   │───────▶│ GenAI spans      │────▶ │ Burnrate SDK │
  │ summarizer-v1   │        │ (token counts)   │      │ (add $$$)    │
  └─────────────────┘        └──────────────────┘      └──────────────┘
         ▲                                                      │
         │                                                      ▼
         │                    6. THROTTLE              4. METRICS
         │                    ┌────────────┐           ┌─────────────┐
         │                    │ POST       │           │ burnrate.   │
         │                    │ /control/  │           │ cost.usd    │
         │                    │ throttle   │           │ (charted)   │
         │                    └────────────┘           └─────────────┘
         │                         ▲                          │
         │                         │                          ▼
         │                  5. RECOVERY                  ┌─────────────┐
         │                  ┌────────────┐               │  SigNoz     │
         └──────────────────│ Cost Guard │◀──────────────│ (dashboards │
                            │ (Claude +  │               │ + alerts)   │
                            │ MCP)       │               └─────────────┘
                            └────────────┘
```

### Container Network

```
┌──────────────────────────────────────────────────────────────────┐
│                Docker Network: signoz-network                     │
│  (created by pours/deployment/compose.yaml)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      SigNoz Stack                           │  │
│  │  signoz-telemetrystore-clickhouse-0-0   (ClickHouse)        │  │
│  │  signoz-metastore-postgres-0            (PostgreSQL)         │  │
│  │  signoz-ingester                        (:4317 OTLP gRPC)   │  │
│  │  signoz-signoz-0                        (:8080 UI)           │  │
│  │  signoz-mcp                             (:8000 MCP)          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                    ▲                                               │
│          ┌─────────┴──────────┐                                   │
│          │                    │                                    │
│  ┌──────────────┐  ┌──────────────────┐                          │
│  │ demo-app     │  │ cost-guard       │ ← also on burnrate net   │
│  │ :8001        │  │ :8082            │                          │
│  └──────────────┘  └──────────────────┘                          │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Key Ports

| Port | Service | Purpose |
|------|---------|---------|
| **8080** | SigNoz UI | Dashboards, alerts, queries |
| **8000** | SigNoz MCP | Cost Guard investigations via AI tools |
| **4317** | SigNoz ingester | OTLP gRPC (demo-app sends spans here) |
| **4318** | SigNoz ingester | OTLP HTTP (alternative) |
| **8001** | Demo App | Chaos injection, batch research endpoints |
| **8082** | Cost Guard | Webhook listener for SigNoz alerts |

---

## Demo Walkthrough

### Scenario 1: Retry Loop (Full Recovery)

Watch Cost Guard detect and stop a retry loop:

```bash
# Terminal 1: (SigNoz already running via foundryctl cast)
docker-compose up   # or 'up -d' if you prefer background

# Terminal 2: Inject the chaos
curl -X POST http://localhost:8001/chaos/activate/retry_loop

# Terminal 3: Generate traffic
curl -X POST "http://localhost:8001/research/batch?count=5"

# Terminal 4: Watch logs
docker logs -f burnrate-demo-app | grep -E "cost|retry|throttle"
docker logs -f burnrate-cost-guard
```

**What you'll see:**

1. **Demo app logs**: `researcher-v1: retry_loop active — cost exploding`
2. **SigNoz dashboard**: burnrate.cost.usd spike (baseline $0.80/min → $6–8/min)
3. **SigNoz alerts**: BurnRateBudgetAlert fires (~60s after chaos starts)
4. **Cost Guard logs**:
   - `BurnRateBudgetAlert received`
   - `MOCK MODE: returning synthetic diagnosis` (or real MCP investigation if COST_GUARD_MOCK=false)
   - `ACTION: throttled researcher-v1 to 2 calls/min`
5. **SigNoz dashboard**: cost drops back to baseline

**Timeline**: Alert → Investigation → Throttle → Recovery = ~60–90 seconds

### Scenario 2: Model Misroute

Requests silently sent to the most expensive model:

```bash
curl -X POST http://localhost:8001/chaos/activate/model_misroute
curl -X POST "http://localhost:8001/research/batch?count=5"
```

Expected cost spike: **8–10× baseline** (misroute to expensive model)

### Scenario 3: Prompt Bloat

Unbounded context growth:

```bash
curl -X POST http://localhost:8001/chaos/activate/prompt_bloat
curl -X POST "http://localhost:8001/research/batch?count=5"
```

Expected: Gradual cost climb as context grows per call.

### Scenario 4: Cache Miss Storm

Prompt cache invalidated on every call:

```bash
curl -X POST http://localhost:8001/chaos/activate/cache_miss_storm
curl -X POST "http://localhost:8001/research/batch?count=5"
```

Expected cost spike: **5–6× baseline** (loses cache discount)

### Reset After Each Scenario

```bash
curl -X POST http://localhost:8001/chaos/deactivate
curl -X POST http://localhost:8001/control/restore
```

---

## Dashboards & Alerts

### First-Time Setup

1. **Import dashboards** — Go to http://localhost:8080 → Dashboards → Import JSON:
   - `dashboards/burnrate-live-cost-monitor.json`
   - `dashboards/burnrate-cost-by-agent.json`
   - `dashboards/burnrate-model-efficiency.json`

2. **Create the alert rule:**
   - Go to Alerts → Create Alert Rule
   - Metric: `burnrate.cost.usd` (rate > `4.00`)
   - Duration: 1 minute
   - Notification channel: Webhook → `http://burnrate-cost-guard:8082/alert`

   > The webhook uses the container name `burnrate-cost-guard` (both services are on `signoz-network`).

   > For local SigNoz UI → host: use `http://host.docker.internal:8082/alert` if the above doesn't resolve.

### Metrics to Monitor

| Metric | What It Measures |
|--------|------------------|
| `burnrate.cost.usd` | Real-time cost per agent per minute |
| `gen_ai.usage.cost.total` | Per-span cost (in span details) |
| `gen_ai.usage.input_tokens` | Input token count |
| `gen_ai.usage.output_tokens` | Output token count |
| `gen_ai.usage.cache_read_input_tokens` | Cache hit tokens (savings) |

---

## Troubleshooting

### SigNoz Won't Start

**Check SigNoz logs:**
```bash
docker compose -f pours/deployment/compose.yaml logs --tail=50 signoz-signoz-0
docker compose -f pours/deployment/compose.yaml logs --tail=50 signoz-telemetrystore-clickhouse-0-0
```

**"Insufficient memory" / ClickHouse crash:**
- Docker Desktop: Preferences → Resources → Memory → **4GB minimum**

**SigNoz UI blank after 2 minutes:**
- Check PostgreSQL: `docker compose -f pours/deployment/compose.yaml logs signoz-metastore-postgres-0`

**foundryctl not found:**
- Install it: `curl -sL https://dl.signoz.io/foundryctl/install.sh | bash`
- Add to PATH if needed: `export PATH="$HOME/.local/bin:$PATH"`

### Burnrate Services Won't Start

**`Error: network signoz-network not found`**
- SigNoz isn't running yet. Run `foundryctl cast` first and wait for the UI at http://localhost:8080.

**`burnrate-demo-app` crashes:**
```bash
docker logs burnrate-demo-app
```
- If `Connection refused` to OTLP endpoint: SigNoz ingester isn't healthy yet. Wait 30 more seconds.

**`burnrate-cost-guard` build fails:**
```bash
docker-compose build --no-cache cost-guard
```
- Needs internet access to download the SigNoz MCP binary from GitHub releases.

### Cost Guard Doesn't Receive Alerts

**No alert webhook logs in cost-guard:**
1. Verify alert rule is saved in SigNoz: Alerts → Alert Rules
2. Verify notification channel webhook URL is set
3. Manually test the webhook:
   ```bash
   curl -X POST http://localhost:8082/alert \
     -H "Content-Type: application/json" \
     -d '{"status":"firing","alerts":[{"labels":{"alertname":"BurnRateBudgetAlert","severity":"critical"},"annotations":{"description":"burnrate.cost.usd exceeded threshold"}}]}'
   ```

**Cost Guard runs but doesn't throttle:**
- Check logs: `docker logs burnrate-cost-guard | grep -i action`
- Mock mode always returns high-confidence diagnosis → throttle should fire.
- If `DEMO_APP_URL` unreachable: verify demo-app is healthy (`curl http://localhost:8001/health`)

### Chaos Injection Doesn't Trigger Alert

1. Verify chaos is active: `curl http://localhost:8001/health` → lists active chaos modes
2. Generate more traffic: `curl -X POST "http://localhost:8001/research/batch?count=10"`
3. Check SigNoz dashboard: look for cost spike in last 2 minutes
4. Verify alert threshold: default is `$4.00/min`. If lower, adjust the rule.

### Port Conflicts

| Error | Fix |
|-------|-----|
| `port 8080 already in use` | `lsof -i :8080 \| kill <PID>` |
| `port 8001 already in use` | `lsof -i :8001 \| kill <PID>` |
| `port 8082 already in use` | `lsof -i :8082 \| kill <PID>` |

---

## Cleanup

### Stop Burnrate Services

```bash
docker-compose down
```

### Stop SigNoz

```bash
docker compose -f pours/deployment/compose.yaml down
```

### Wipe All Data

```bash
docker-compose down
docker compose -f pours/deployment/compose.yaml down -v
```

The `-v` flag removes ClickHouse and PostgreSQL volumes — all telemetry data is erased. Re-run `foundryctl cast` to bring SigNoz back up fresh.

### Remove Built Images

```bash
docker rmi burnrate-demo-app burnrate-cost-guard
```

---

## Next Steps

1. **Integrate the SDK with your own agents**: One line — `provider.add_span_processor(BurnrateSpanProcessor())`
2. **Set real thresholds**: Adjust alert rules based on your actual cost budget.
3. **Switch to real LLM investigations**: Set `COST_GUARD_MOCK=false` and `ANTHROPIC_API_KEY=sk-ant-...` in `.env`
4. **SigNoz Cloud**: Replace self-hosted SigNoz with SigNoz Cloud by updating the three env vars in `.env` (`SIGNOZ_API_URL`, `SIGNOZ_API_KEY`, `OTLP_ENDPOINT`).

---

## Support

- **SigNoz Docs**: https://signoz.io/docs/
- **OpenTelemetry Docs**: https://opentelemetry.io/docs/
- **Burnrate GitHub**: https://github.com/siddhardh-7/BurnRate

---

**Happy cost-guarding.**
