# Burnrate

<p align="center">
  <strong>The OpenTelemetry GenAI spec tracks every token your agents consume.<br>It tracks zero dollars.</strong>
</p>

<p align="center">
  <a href="https://www.wemakedevs.org/hackathons/signoz"><img src="https://img.shields.io/badge/Agents_of_SigNoz-Hackathon_2026-7c4dff" alt="Agents of SigNoz 2026"></a>
  <a href="https://opentelemetry.io"><img src="https://img.shields.io/badge/OpenTelemetry-native-f5a800" alt="OpenTelemetry"></a>
  <img src="https://img.shields.io/badge/PyPI-coming_soon-lightgrey" alt="PyPI coming soon">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-green" alt="Apache 2.0"></a>
</p>

<p align="center">
  <strong><a href="https://siddhardh-7.github.io/BurnRate/">🌐 View the interactive website →</a></strong> · <a href="SETUP.md"><strong>📖 Deployment guide</strong></a>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> · <a href="#cost-guard-agent">Cost Guard</a> · <a href="#dashboards">Dashboards</a> · <a href="#semconv-proposal">Semconv Proposal</a> · <a href="#chaos-demo-scenarios">Demo</a>
</p>

---

## The Problem That Wakes You Up at 3am

Your agent retried a failed call in a loop. No circuit breaker. By morning, it had made 847 LLM calls instead of 20. Token counts were in your traces the whole time — but nobody translated them to dollars, nobody knew which agent spent them, and no alert fired until the invoice arrived.

This is not a tooling problem. It is a **specification gap**.

```
gen_ai.usage.input_tokens            ✅  in OTel GenAI semconv (v1.27+)
gen_ai.usage.output_tokens           ✅
gen_ai.usage.cache_read_input_tokens ✅
gen_ai.usage.cost.total              ❌  does not exist — we propose it
gen_ai.usage.cost.input              ❌
gen_ai.usage.cost.cache_read         ❌
```

The spec tracks consumption. It never standardized what consumption costs. Every team that wants cost visibility must implement model-specific pricing logic outside the tracing layer, creating duplicate work, inconsistent numbers, and zero cross-team standardization.

**Burnrate closes the gap.**

A zero-config OpenTelemetry SpanProcessor that enriches every GenAI span with real dollar costs, streams per-agent cost metrics into SigNoz, and deploys a Cost Guard agent that catches runaway spend, diagnoses the culprit through SigNoz's official MCP server, and acts before the bill explodes.

---

## What You Get in 60 Seconds

**1. Cost-enriched traces** — every GenAI span gains `gen_ai.usage.cost.total` and a full breakdown (input, output, cache, reasoning). Visible in SigNoz traces instantly.

**2. Per-agent cost metrics** — `burnrate.cost.usd` flows as an OTel Counter with dimensions `burnrate.agent.id`, `gen_ai.request.model`, `service.name`. Drives the dashboards and alert rules.

**3. Autonomous cost defense** — Cost Guard wakes on a SigNoz alert, investigates via the SigNoz MCP server, throttles the culprit agent, and files an incident report — all without a human on-call.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Your AI Agent System                                                │
│  (LangChain · LangGraph · raw Anthropic/OpenAI SDK · anything)       │
│                                                                      │
│   gen_ai.usage.input_tokens ─────────────────────────────────┐      │
│   gen_ai.usage.output_tokens                                  │      │
│   gen_ai.usage.cache_read_input_tokens                        ▼      │
│                                                 BurnrateSpanProcessor│
│                                                 ↓ gen_ai.usage.cost.*│
│                                                 ↓ burnrate.cost.usd  │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ OTLP  gRPC :4317 / HTTP :4318
                                   ▼
              ┌─────────────────────────────────────────┐
              │              SigNoz                     │
              │  Traces  ·  Metrics  ·  Alerts          │
              │  3 importable dashboards                │
              │  Budget alert rule                      │
              └───────────────────┬─────────────────────┘
                                  │ webhook (alert fires)
                                  ▼
              ┌─────────────────────────────────────────┐
              │           Cost Guard Agent              │
              │                                         │
              │  1. Receives SigNoz alert               │
              │  2. Investigates via SigNoz MCP :8000   │
              │     (queries traces · metrics · logs)   │
              │  3. Diagnoses culprit agent + root cause│
              │  4. Throttles via demo-app control API  │
              │  5. Files Slack incident report         │
              └─────────────────────────────────────────┘
```

The Cost Guard uses **SigNoz's official MCP server** — it doesn't call SigNoz APIs directly. This means it gets the full power of SigNoz's query engine through a stable, AI-native interface.

---

## Quickstart

```bash
git clone https://github.com/siddhardh-7/BurnRate.git
cd BurnRate
cp .env.example .env        # fill in ANTHROPIC_API_KEY (or leave COST_GUARD_MOCK=true)

# Install SigNoz via Foundry (reads casting.yaml, starts SigNoz + MCP server)
foundryctl cast

# Then start Burnrate services (joins SigNoz network automatically)
docker-compose up --build
```

Then in another terminal:

```bash
# Start the research pipeline (normal cost)
curl -X POST "http://localhost:8001/research/batch?count=3"

# Inject a retry loop chaos scenario — costs spike 8-10×
curl -X POST "http://localhost:8001/chaos/activate/retry_loop"
curl -X POST "http://localhost:8001/research/batch?count=5"

# Watch the SigNoz alert fire → Cost Guard diagnose → throttle → cost drops
```

---

## SDK Installation

```bash
git clone https://github.com/siddhardh-7/BurnRate.git
cd BurnRate
uv pip install -e packages/burnrate-otel
```

```python
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from burnrate import BurnrateSpanProcessor

# MeterProvider must come first — BurnrateSpanProcessor captures it at init time.
metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))

provider = TracerProvider()
provider.add_span_processor(BurnrateSpanProcessor())  # ← one line. zero config.
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
```

**That is the entire integration.** No model configuration. No pricing setup. Any GenAI span that carries `gen_ai.usage.input_tokens` and `gen_ai.request.model` gets cost-enriched automatically.

---

## What Lands on Your Spans

```json
{
  "name": "gen_ai chat",
  "attributes": {
    "gen_ai.system": "anthropic",
    "gen_ai.request.model": "claude-haiku-4-5-20251001",
    "gen_ai.usage.input_tokens": 1842,
    "gen_ai.usage.output_tokens": 312,
    "gen_ai.usage.cache_read_input_tokens": 1200,

    "gen_ai.usage.cost.total":          0.00220576,
    "gen_ai.usage.cost.input":          0.00147360,
    "gen_ai.usage.cost.output":         0.00124800,
    "gen_ai.usage.cost.cache_read":     0.00009600,
    "gen_ai.usage.cost.currency":       "USD",
    "gen_ai.usage.cost.pricing_model":  "per_token",

    "burnrate.agent.id":   "researcher-v1",
    "burnrate.task.id":    "research:ai-observability",
    "burnrate.user.id":    "user_a9f3c1"
  }
}
```

The `burnrate.agent.id` / `task.id` / `user.id` dimensions are the FinOps layer — they let you answer "which team, which agent, which feature is burning budget?" the same way cloud infrastructure cost is attributed today.

---

## Supported Models

| Provider | Models |
|---|---|
| **Anthropic** | claude-opus-4-8, claude-sonnet-4-6, claude-fable-5, claude-haiku-4-5, claude-3-5-sonnet, claude-3-5-haiku |
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-4-turbo, o3, o3-mini, o4-mini (incl. reasoning tokens) |
| **Google** | gemini-2.5-pro, gemini-2.5-flash, gemini-1.5-pro |

Unknown models log a warning and record `cost = 0.0` — never silently wrong. Add your model to the [bundled pricing table](packages/burnrate-otel/src/burnrate/pricing.py) or override at runtime via `BURNRATE_PRICING_FILE`.

---

## Dashboards

Import all three from the `dashboards/` directory into SigNoz (**Settings → Dashboards → Import**):

| Dashboard | Purpose |
|---|---|
| **Burnrate — Live Cost Monitor** | Real-time $/s by agent and by model — your cost vital sign |
| **Burnrate — Cost by Agent & Task** | Table: who spent what. Time series: when the spike happened |
| **Burnrate — Model Efficiency** | Cost rate by model, model vs. agent breakdown, cumulative spend |

All panels use `burnrate.cost.usd` grouped by `burnrate.agent.id` or `gen_ai.request.model`. They show data immediately — no additional configuration.

---

## Cost Guard Agent

### What it does

Cost Guard is a Claude-powered incident response agent that turns SigNoz budget alerts into automated investigations and actions.

When a budget alert fires:

1. **Receives** the SigNoz webhook at `POST /alert`
2. **Connects** to SigNoz's official MCP server (port 8000, via `signoz-mcp` container on the shared Docker network) — 8 cost-relevant tools available
3. **Investigates** via a multi-turn tool-use loop: queries `burnrate.cost.usd` metrics, searches traces for the culprit agent, inspects token counts and retry patterns
4. **Diagnoses** — root cause, culprit agent, culprit operation, evidence, estimated hourly cost
5. **Acts** — throttles the culprit via the demo app's control API; burn rate drops within 60 seconds
6. **Reports** — structured incident report to Slack (or stdout if no webhook configured)

### Sample incident report

```
🔥 BurnRateBudgetAlert — CRITICAL

Summary: researcher-v1 stuck in retry loop causing 9.3× cost spike on burnrate-demo-app

Culprit: researcher-v1 → gen_ai chat
Root cause: researcher-v1 making 8-12 LLM calls per task instead of 1.
  Each failed attempt logs a RateLimitError. Input tokens grew from ~170
  (baseline) to ~1,400 per task due to accumulated retry context.
  Burn rate: $0.0003/min → $0.0028/min

Cost impact: $10.98/hr  ·  $263/day projected

Evidence:
  • burnrate.cost.usd rate: 0.000047/s → 0.000183/s (3.9× above threshold)
  • researcher-v1 span count: 47 in 15 min vs 5 baseline (9.4× normal)
  • gen_ai.usage.input_tokens p95: 1,387 vs 171 baseline
  • demo.simulated_failure=true on 8 of 10 spans — retry loop confirmed

Actions taken by Cost Guard:
  ✓ Throttled researcher-v1 to 2 calls/min — burn rate dropping now

Recommended next steps:
  1. Add exponential backoff with MAX_RETRIES = 3
  2. Add per-agent hourly budget cap of $2.00
  3. Route retries to haiku instead of sonnet
```

### Setup

In SigNoz **Settings → Notification Channels**, create a Webhook channel.

**Docker Compose** (both SigNoz and Cost Guard on `signoz-network`):
```
http://burnrate-cost-guard:8082/alert
```

**Local development** (SigNoz in Docker via foundryctl, Cost Guard running via `uv run`):
```
http://host.docker.internal:8082/alert
```

> Never use `localhost` — it resolves to the SigNoz container itself, not your host machine.

### Mock mode

Cost Guard runs in mock mode by default (`COST_GUARD_MOCK=true`). It returns a realistic synthetic diagnosis without consuming Anthropic credits — the full E2E loop (alert → investigate → throttle → report) works immediately out of the box.

Switch to real LLM investigation:

```bash
# .env
COST_GUARD_MOCK=false
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Chaos Demo Scenarios

The demo app (port **8001**) ships four injectable cost failure modes:

```bash
# Retry loop — researcher retries every call 8-12x. Cost spikes 8-10×.
curl -X POST http://localhost:8001/chaos/activate/retry_loop

# Model misroute — cheap tasks routed to expensive model. Cost spikes 20×.
curl -X POST http://localhost:8001/chaos/activate/model_misroute

# Prompt bloat — context grows unbounded across calls. Cost compounds per call.
curl -X POST http://localhost:8001/chaos/activate/prompt_bloat

# Cache miss storm — prompt variations defeat Anthropic caching. Cache savings lost.
curl -X POST http://localhost:8001/chaos/activate/cache_miss_storm

# Return to baseline
curl -X POST http://localhost:8001/chaos/deactivate
```

Generate traffic:
```bash
curl -X POST "http://localhost:8001/research/batch?count=5"
```

Watch `burnrate-demo-app → researcher-v1` spike in the Live Cost Monitor dashboard. Wait for Cost Guard to throttle it. Watch the spike subside.

---

## Semconv Proposal

The `gen_ai.usage.cost.*` attributes in this project are **not yet in the OpenTelemetry GenAI semantic conventions**. They should be.

[`docs/semconv-proposal.md`](docs/semconv-proposal.md) is a complete upstream proposal — written to OTel OTEP conventions — covering:

- Why the gap is structural, not incidental
- Pricing variation across providers that makes a single multiplier insufficient
- Full attribute schema with requirement levels and calculation specification
- Design decisions (why `cost.*` not a single scalar, why span attributes not just metrics)
- Rejected alternatives (let the platform compute it; use API response cost fields)
- Open questions (regional pricing, batch API, streaming, multi-model calls)

The proposal's next step is a GitHub Discussion in `open-telemetry/semantic-conventions` and a draft PR against the GenAI spans spec. Burnrate is the reference implementation.

If standardized, `gen_ai.usage.cost.total` would let SigNoz, Grafana, Datadog, and Honeycomb render first-class cost dashboards from any OTel-instrumented app with zero configuration — the same way `gen_ai.usage.input_tokens` already does for token counts.

---

## AWS Deployment

```bash
# EC2 — Ubuntu 24.04, t3.medium or larger (4GB RAM minimum)
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
curl -sL https://dl.signoz.io/foundryctl/install.sh | bash
git clone https://github.com/siddhardh-7/BurnRate.git && cd BurnRate
cp .env.example .env && nano .env   # fill in ANTHROPIC_API_KEY

# Install SigNoz via Foundry (casting.yaml + casting.yaml.lock are in the repo)
foundryctl cast

# Start Burnrate services
docker compose up -d

# SigNoz notification channel webhook URL (container name resolves on signoz-network):
# http://burnrate-cost-guard:8082/alert
```

---

## Project Structure

```
burnrate/
├── packages/burnrate-otel/     # pip-installable SDK (core deliverable)
│   └── src/burnrate/
│       ├── processor.py        # OTel SpanProcessor — the cost enrichment layer
│       ├── pricing.py          # Per-model pricing table (hot-reloadable JSON)
│       ├── metrics.py          # OTel Counter + Histogram for cost metrics
│       └── semconv.py          # Proposed gen_ai.usage.cost.* attribute names
├── cost-guard/                 # Claude + SigNoz MCP incident agent
│   └── src/guard/
│       ├── webhook.py          # FastAPI — receives SigNoz alerts
│       ├── investigate.py      # MCP client → Claude tool-use loop
│       ├── actions.py          # Throttle / restore demo-app agents
│       └── report.py           # Slack incident report formatter
├── demo-app/                   # Multi-agent pipeline + chaos injection (port 8001)
│   └── src/demo/
│       ├── app.py              # FastAPI + OTel setup
│       ├── agents/             # researcher-v1, summarizer-v1
│       └── chaos.py            # Injectable failure modes
├── dashboards/                 # Three importable SigNoz dashboard JSONs
├── alerts/                     # SigNoz alert rule YAML definitions
└── docs/
    ├── semconv-proposal.md     # Upstream OTel spec proposal
    └── demo-script.md          # 3-minute live demo script
```

---

## Ports Reference

| Service | Port | Purpose |
|---|---|---|
| SigNoz UI | 8080 | Dashboards · traces · alert rules |
| SigNoz MCP | 8000 | AI tool access (`/mcp`) for Cost Guard |
| OTLP gRPC | 4317 | Trace + metric ingestion |
| OTLP HTTP | 4318 | Trace + metric ingestion (alternative) |
| Demo App | 8001 | Research pipeline + chaos control |
| Cost Guard | 8082 | SigNoz alert webhook receiver |

---

## Built With

- [SigNoz](https://signoz.io) — OpenTelemetry-native observability backend (traces · metrics · logs · alerts · MCP)
- [OpenTelemetry Python SDK](https://opentelemetry.io) — vendor-neutral instrumentation
- [Anthropic Claude](https://anthropic.com) — Cost Guard reasoning engine
- [AWS EC2](https://aws.amazon.com/ec2/) — deployment infrastructure

---

## Contributing

Pricing tables go stale. If your model is missing or wrong, open a PR against [`packages/burnrate-otel/src/burnrate/pricing.py`](packages/burnrate-otel/src/burnrate/pricing.py). One dict entry, one PR.

For the semconv proposal, see [`docs/semconv-proposal.md`](docs/semconv-proposal.md) and the OTel GenAI SIG meeting schedule.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

<p align="center">
  Built for the <a href="https://www.wemakedevs.org/hackathons/signoz">Agents of SigNoz Hackathon</a>, July 2026.<br>
  <em>Token counts don't pay the bill. Dollars do.</em>
</p>
