# Burnrate — Setup & Deployment Guide

Complete walkthrough for judges and anyone deploying the Burnrate project locally.

## Table of Contents

1. [Quick Start](#quick-start) — Get everything running in 60 seconds
2. [Prerequisites](#prerequisites) — What you need installed
3. [Architecture Overview](#architecture-overview) — How the pieces fit together
4. [Demo Walkthrough](#demo-walkthrough) — Step-by-step chaos injection & recovery
5. [Dashboards & Alerts](#dashboards--alerts) — Where to watch the action
6. [Troubleshooting](#troubleshooting) — Common issues & fixes
7. [Cleanup](#cleanup) — Tear down safely

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/siddhardh-7/BurnRate.git
cd BurnRate
```

### 2. Set up environment variables

Create a `.env` file in the project root:

```bash
cat > .env <<EOF
# Anthropic API key (required for Cost Guard to investigate)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# SigNoz API key (optional for real dashboards, mock mode works without it)
SIGNOZ_API_KEY=

# Cost Guard mock mode (set to false for real LLM investigations)
COST_GUARD_MOCK=true
EOF
```

> **Note**: If you don't have an Anthropic API key, `COST_GUARD_MOCK=true` simulates the investigation loop without making real API calls.

### 3. Start the full stack

```bash
docker-compose up --build
```

**Wait for all services to be healthy** — you'll see:
- `burnrate-clickhouse`: "ClickHouse is ready."
- `burnrate-otel-collector`: "Everything is ready. Begin!"
- `burnrate-signoz`: "Listening on :8080"
- `burnrate-demo-app`: Ready on port 8001
- `burnrate-cost-guard`: Webhook listening on port 8082

Expected startup time: **45–90 seconds** depending on your machine.

### 4. Open the dashboard

Visit **http://localhost:8080** in your browser:
- Default login: no credentials needed (self-hosted mode)
- Click "Dashboards" → Look for **"Burnrate Live Cost Monitor"** (may need to be created, see [Dashboards](#dashboards--alerts))

### 5. Run a demo scenario

In a separate terminal, inject a chaos failure:

```bash
# Inject a retry loop on researcher-v1
curl -X POST http://localhost:8001/chaos/activate/retry_loop

# Generate traffic to trigger the failure
curl -X POST "http://localhost:8001/research/batch?count=5"

# Watch the logs in another terminal:
docker logs -f burnrate-demo-app
docker logs -f burnrate-cost-guard
```

Then open http://localhost:8080 and watch:
- **SigNoz Metrics** → burnrate.cost.usd climbs in real time
- **Alert fires** → BurnRateBudgetAlert triggered (check Alerts section)
- **Cost Guard logs** → Investigates via SigNoz MCP, diagnoses, throttles
- **Cost recovers** → Demo app throttles researcher-v1, spend drops to baseline

### 6. Restore and reset

```bash
# Clear the chaos injection
curl -X POST http://localhost:8001/chaos/deactivate

# Restore all agents to normal
curl -X POST http://localhost:8001/control/restore
```

---

## Prerequisites

### Required

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
  - Check: `docker --version && docker-compose --version`
- **Curl** or a REST client (for chaos injection)
  - Check: `curl --version`
- **4GB+ RAM** (SigNoz + ClickHouse uses ~1–2GB)

### Optional

- **Anthropic API key** (free at https://console.anthropic.com)
  - For real Cost Guard investigations (without it, mock mode runs)
- **SigNoz Cloud API key** (if using SigNoz Cloud instead of self-hosted)

### System Requirements

| Component | CPU | Memory | Disk |
|-----------|-----|--------|------|
| ClickHouse | 1 core | 512MB | 500MB |
| OTel Collector | 0.5 core | 256MB | 50MB |
| SigNoz Server | 1 core | 512MB | 100MB |
| Demo App | 0.5 core | 256MB | 50MB |
| Cost Guard | 0.5 core | 256MB | 50MB |
| **Total** | **~3 cores** | **~2GB** | **~750MB** |

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
┌─────────────────────────────────────────────┐
│         Docker Network: burnrate             │
├─────────────────────────────────────────────┤
│                                               │
│  ┌──────────────────────────────────────┐   │
│  │         SigNoz Stack                  │   │
│  │  ┌─────────────┐  ┌────────────────┐ │   │
│  │  │ ClickHouse  │  │ OTel Collector │ │   │
│  │  │ (traces)    │  │ (receives)     │ │   │
│  │  └─────────────┘  └────────────────┘ │   │
│  │  ┌──────────────────────────────────┐ │   │
│  │  │  SigNoz Server                    │ │   │
│  │  │  :8080 (UI) :8000 (MCP)           │ │   │
│  │  └──────────────────────────────────┘ │   │
│  └──────────────────────────────────────┘   │
│                    ▲                          │
│                    │ :4317 (OTLP gRPC)       │
│          ┌─────────┴──────────┐              │
│          │                    │              │
│  ┌──────────────┐  ┌──────────────────┐     │
│  │ demo-app     │  │ cost-guard       │     │
│  │ :8001        │  │ :8082            │     │
│  │ (agents)     │  │ (webhook)        │     │
│  └──────────────┘  └──────────────────┘     │
│                                               │
└─────────────────────────────────────────────┘
```

### Key Ports

| Port | Service | Purpose |
|------|---------|---------|
| **8080** | SigNoz UI | Dashboards, alerts, queries |
| **8000** | SigNoz MCP | Cost Guard investigations |
| **4317** | OTel Collector | OTLP gRPC (demo-app sends spans) |
| **4318** | OTel Collector | OTLP HTTP (alternative) |
| **8001** | Demo App | Chaos injection, batch research endpoints |
| **8082** | Cost Guard | Webhook listener for SigNoz alerts |

---

## Demo Walkthrough

### Scenario 1: Retry Loop (Automatic Recovery)

Watch Cost Guard detect and stop a retry loop:

```bash
# Terminal 1: Start the stack
docker-compose up

# Terminal 2: Inject the chaos
curl -X POST http://localhost:8001/chaos/activate/retry_loop

# Terminal 3: Generate traffic
curl -X POST "http://localhost:8001/research/batch?count=5"

# Terminal 4: Watch logs
docker logs -f burnrate-demo-app | grep -E "cost|retry|throttle"
docker logs -f burnrate-cost-guard | grep -E "alert|investigation|throttle"
```

**What you'll see:**

1. **Demo app logs**: "researcher-v1: retry_loop active — cost exploding"
2. **SigNoz dashboard**: burnrate.cost.usd spike (goes from $0.80/min to $6–8/min)
3. **SigNoz alerts**: BurnRateBudgetAlert fires (~60s after chaos starts)
4. **Cost Guard logs**:
   - `[signoz] BurnRateBudgetAlert received`
   - `[mcp] metrics_query: researcher-v1 = 94% of spend`
   - `[mcp] trace_search: error status repeating — retry loop detected`
   - `[guard] diagnosis: researcher-v1 retrying a failing call`
   - `[guard] action: POST /control/throttle researcher-v1`
5. **Demo app logs**: "researcher-v1 throttled — spend decaying"
6. **SigNoz dashboard**: cost drops back to baseline

**Timeline**: Alert → Investigation → Throttle → Recovery = ~60–90 seconds

### Scenario 2: Model Misroute

Requests silently sent to the most expensive model:

```bash
curl -X POST http://localhost:8001/chaos/activate/model_misroute
curl -X POST "http://localhost:8001/research/batch?count=5"
```

Expected cost spike: **8–10× baseline** (misroute to claude-opus instead of haiku)

### Scenario 3: Prompt Bloat

Unbounded context growth:

```bash
curl -X POST http://localhost:8001/chaos/activate/prompt_bloat
curl -X POST "http://localhost:8001/research/batch?count=5"
```

Expected: Gradual cost climb as context grows per call

### Scenario 4: Cache Miss Storm

Prompt cache invalidated on every call:

```bash
curl -X POST http://localhost:8001/chaos/activate/cache_miss_storm
curl -X POST "http://localhost:8001/research/batch?count=5"
```

Expected cost spike: **5–6× baseline** (loses 90% cache discount)

### Reset After Each Scenario

```bash
# Clear the chaos injection
curl -X POST http://localhost:8001/chaos/deactivate

# Restore all agents
curl -X POST http://localhost:8001/control/restore
```

---

## Dashboards & Alerts

### First-Time Setup

1. **Create the "Burnrate Live Cost Monitor" dashboard:**
   - Go to http://localhost:8080 → Dashboards → Create Dashboard
   - Add a panel with metric: `burnrate.cost.usd`
   - Group by: `burnrate.agent.id`
   - Time range: Last 5 minutes, auto-refresh 1s

2. **Create the "BurnRateBudgetAlert" alert rule:**
   - Go to Alerts → Create Alert Rule
   - Metric: `burnrate.cost.usd` > `4.00` ($/min threshold)
   - Duration: 1 minute
   - Notification channel: Webhook → `http://cost-guard:8082/alert`

> **Tip**: Pre-configured dashboards are in `dashboards/` — you can import them via the SigNoz UI.

### Metrics to Monitor

| Metric | What It Measures |
|--------|------------------|
| `burnrate.cost.usd` | Real-time cost per agent per minute |
| `gen_ai.usage.cost.total` | Per-span cost (in span details) |
| `gen_ai.usage.input_tokens` | Input token count |
| `gen_ai.usage.output_tokens` | Output token count |
| `gen_ai.usage.cache_read_tokens` | Cache hit tokens (savings) |

### Sample Queries

**Cost by agent over last hour:**
```
SELECT agent_id, SUM(cost) as total_cost
FROM burnrate_cost_usd
WHERE timestamp > now() - 1h
GROUP BY agent_id
```

**Trace that cost the most:**
```
SELECT trace_id, gen_ai_usage_cost_total, model
FROM traces
ORDER BY gen_ai_usage_cost_total DESC
LIMIT 1
```

---

## Troubleshooting

### Container Won't Start

**Error: `port 8080 already in use`**
- Another service is using the port. Kill it:
  ```bash
  lsof -i :8080
  kill <PID>
  ```
- Or change the port in `docker-compose.yml`: `"8000:8080"` (host:container)

**Error: `docker: not found`**
- Docker is not installed. Install from https://docs.docker.com/get-docker/

**Error: `Insufficient memory`**
- ClickHouse needs ~1GB. Increase Docker's memory limit:
  - Docker Desktop: Preferences → Resources → Memory → 4GB+
  - Docker Daemon: Edit `/etc/docker/daemon.json` → `"memory": "4g"`

### Services Don't Become Healthy

Check logs:
```bash
docker-compose logs --tail=50 clickhouse
docker-compose logs --tail=50 otel-collector
docker-compose logs --tail=50 signoz-server
```

**ClickHouse logs show "Cannot allocate memory":**
- Reduce Docker's resource limits or restart Docker daemon.

**OTel Collector won't export:**
- Verify ClickHouse is healthy: `docker exec burnrate-clickhouse clickhouse-client -q "SELECT 1"`

**SigNoz UI blank:**
- Wait another 30s for ClickHouse to initialize.
- Check browser console for errors (F12).

### Demo App Can't Send Spans

**Error: `Connection refused to otel-collector:4317`**
- OTel Collector is down. Check: `docker logs burnrate-otel-collector`

**Error: `ANTHROPIC_API_KEY not found`**
- The `.env` file is missing or invalid. Recreate it (see [Quick Start](#quick-start)).

### Cost Guard Doesn't Receive Alerts

**No logs in `cost-guard`:**
1. Check alert rule is configured: SigNoz Alerts → Notification Channels
2. Webhook URL: `http://cost-guard:8082/alert`
3. Manually test: `curl -X POST http://localhost:8082/alert -H "Content-Type: application/json" -d '{"status":"firing"}'`

**Mock mode not working:**
- Check `.env`: `COST_GUARD_MOCK=true`
- Check logs: `docker logs burnrate-cost-guard | grep -i mock`

### Chaos Injection Doesn't Trigger Alert

**Expected: Cost spikes when injecting chaos**

1. Verify chaos is active: `curl http://localhost:8001/health` → should list active chaos modes
2. Generate traffic: `curl -X POST "http://localhost:8001/research/batch?count=10"` (larger batch)
3. Check SigNoz dashboard: Refresh and look for cost spike in the last 2 minutes
4. Verify alert threshold: Default is `$4.00/min`. If chaos cost is lower, raise the threshold or lower it.

---

## Cleanup

### Stop All Services

```bash
docker-compose down
```

### Wipe All Data

```bash
docker-compose down -v
```

This removes:
- All containers
- All volumes (ClickHouse data, SigNoz state)
- All networks

### Free Up Ports

If you want to reclaim ports without stopping containers:
```bash
docker-compose down
```

### Remove Local Docker Images

```bash
docker rmi burnrate-demo-app burnrate-cost-guard signoz/signoz clickhouse/clickhouse-server
```

---

## Next Steps

1. **Integrate with your own agents**: Replace demo-app with your LangChain/LangGraph agents. The SDK is one line: `provider.add_span_processor(BurnrateSpanProcessor())`
2. **Set real thresholds**: Adjust alert rules based on your cost budget.
3. **Add dashboards**: Import `dashboards/` JSONs into your SigNoz instance.
4. **Deploy Cost Guard**: Run cost-guard as a persistent service (ECS, Lambda, Cloud Run) to handle alerts in production.

---

## Support

- **SigNoz Docs**: https://signoz.io/docs/
- **OpenTelemetry Docs**: https://opentelemetry.io/docs/
- **Burnrate GitHub**: https://github.com/siddhardh-7/BurnRate
- **Issues**: Open an issue on GitHub or email the team.

---

**Happy cost-guarding!** 🔥
