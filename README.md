# Burnrate — FinOps for AI Agents

> *"Know what every token costs — and which agent spent it."*

[![Built for Agents of SigNoz Hackathon](https://img.shields.io/badge/Agents_of_SigNoz-Hackathon_2026-blue)](https://www.wemakedevs.org/hackathons/signoz)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-native-7c4dff)](https://opentelemetry.io)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

The OTel GenAI semantic conventions track every token. They track **zero dollars**.

Burnrate fills the gap: a zero-config OpenTelemetry SpanProcessor that enriches your AI agent spans with real dollar costs and streams per-agent, per-task, per-user cost metrics into SigNoz — plus a Cost Guard agent that catches runaway spend before the bill lands.

---

## The Problem (It's in the Spec)

```
gen_ai.usage.input_tokens   ✅  (exists in OTel GenAI semconv)
gen_ai.usage.output_tokens  ✅
gen_ai.usage.cost.total     ❌  (does not exist — we propose it)
```

See [docs/semconv-proposal.md](docs/semconv-proposal.md) for the full proposal to add `gen_ai.usage.cost.*` to the upstream spec.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Your AI Agent System (LangChain, LangGraph, etc.)  │
│         │  OTel GenAI spans                         │
│         ▼                                           │
│  burnrate-otel SpanProcessor (one line to add)      │
│  → enriches spans with gen_ai.usage.cost.*          │
│  → emits burnrate.cost.usd metrics by agent/task    │
└──────────────┬──────────────────────────────────────┘
               │ OTLP
               ▼
         SigNoz Cloud
    (traces · metrics · alerts)
               │ alert webhook
               ▼
      Cost Guard Agent (Claude + SigNoz MCP)
      → diagnoses culprit → acts → Slack report
```

---

## Quick Start

```bash
git clone https://github.com/yourusername/burnrate
cd burnrate
cp .env.example .env   # add SIGNOZ_API_KEY + ANTHROPIC_API_KEY
docker-compose up
```

**Or install the SDK directly:**

```bash
pip install burnrate-otel
```

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from burnrate import BurnrateSpanProcessor

provider = TracerProvider()
provider.add_span_processor(BurnrateSpanProcessor())  # ← this is all you need
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
```

Your GenAI spans now carry `gen_ai.usage.cost.total` (and breakdown by input/output/cache/reasoning). Cost metrics flow to SigNoz automatically.

---

## What You Get in SigNoz

### Dashboards (import from `dashboards/`)

| Dashboard | File | What it shows |
|---|---|---|
| **Burn Rate Live** | `burn-rate-live.json` | Real-time $/min by agent — your cost vital sign |
| **Cost by Agent & Task** | `cost-by-agent.json` | Which agent is spending what, on which tasks |
| **Model Efficiency** | `model-efficiency.json` | Cache hit rates, cost/output token, model distribution |

### Alert Rules (import from `alerts/`)

- **Budget Burn Rate** — fires when $/hr exceeds threshold
- **Per-Agent Anomaly** — fires when a single agent's cost spikes >3× its baseline
- **Cost per Task Spike** — fires when individual task cost exceeds ceiling

---

## Cost Guard Agent

Cost Guard watches SigNoz alerts. When a budget alert fires, it:

1. **Investigates** via the [official SigNoz MCP server](https://signoz.io/docs/ai/signoz-mcp-server/) — querying traces, metrics, and logs to find the culprit
2. **Diagnoses** — which agent, which operation, which failure pattern (retry loop, model misroute, prompt bloat, cache miss storm)
3. **Acts** — throttles the culprit agent via the demo app's control API (burn rate drops within 60s)
4. **Reports** — structured Slack incident report with dollar impact, evidence, and actions taken

Example Slack output:
```
🔥 Budget Burn Rate Alert — CRITICAL
Summary: researcher-agent stuck in a 42-iteration retry loop on topic "LLM trends"
Culprit: researcher-v1 → invoke_agent
Root cause: Error handling bug causes unbounded retries. Each retry consumes ~78k tokens
            on claude-sonnet-4-6 (vs expected haiku). Context grows with each iteration.
Cost impact: $5.80/hr · $139/day projected
Confidence: high
Evidence:
  • burnrate.cost.usd{agent=researcher-v1}: 0.14 → 5.8 $/hr (41× spike at 14:32)
  • 847 spans from researcher-v1 in last 10 min (baseline: 20)
  • Trace abc123: 42 child spans all with status=ERROR then retry
Actions taken by Cost Guard:
  ✓ Throttled `researcher-v1` to 2 calls/min — burn rate will drop within 60s
Recommended next steps:
  1. Kill researcher-v1 retry loop — set MAX_RETRIES=3
  2. Route topic-research tasks back to haiku (not sonnet)
  3. Add circuit breaker to ResearchAgent.run()
```

---

## Cost Attribution Dimensions

Add these attributes to your spans for Cost Guard to track spend precisely:

```python
span.set_attribute("burnrate.agent.id", "researcher-v1")
span.set_attribute("burnrate.task.id", "research:ai-trends")
span.set_attribute("burnrate.user.id", "user_abc123")
span.set_attribute("burnrate.feature", "research-pipeline")
```

---

## Chaos Demo Scenarios

The demo app ships four injectable cost failure modes for live demos:

```bash
# Start a cost spike — researcher retries every call 8-12 times
curl -X POST http://localhost:8000/chaos/activate/retry_loop

# Route all cheap tasks to an expensive model (20× cost)
curl -X POST http://localhost:8000/chaos/activate/model_misroute

# Context accumulates without summarization (cost grows per call)
curl -X POST http://localhost:8000/chaos/activate/prompt_bloat

# Slight prompt variations defeat Anthropic caching (cache savings lost)
curl -X POST http://localhost:8000/chaos/activate/cache_miss_storm

# Back to normal
curl -X POST http://localhost:8000/chaos/deactivate
```

---

## Semconv Proposal

The `gen_ai.usage.cost.*` attributes proposed here are missing from the upstream OTel GenAI semantic conventions. This project ships a reference implementation and a [formal proposal](docs/semconv-proposal.md) for the upstream spec — with the goal of standardizing LLM cost observability across the ecosystem.

---

## Deployment (AWS)

```bash
# EC2 (Ubuntu 24.04, t3.medium)
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
git clone https://github.com/yourusername/burnrate && cd burnrate
cp .env.example .env && nano .env  # fill in keys
docker compose up -d
```

Configure your SigNoz alert webhook to point to `http://<ec2-ip>:8080/alert`.

---

## Project Structure

```
burnrate/
├── packages/burnrate-otel/   # pip-installable SDK (the core)
├── cost-guard/               # Claude + SigNoz MCP incident agent
├── demo-app/                 # Multi-agent demo with chaos injection
├── dashboards/               # Importable SigNoz dashboard JSONs
├── alerts/                   # SigNoz alert rule YAML definitions
└── docs/semconv-proposal.md  # Formal proposal: gen_ai.usage.cost.*
```

---

## Built With

- [SigNoz](https://signoz.io) — OpenTelemetry-native observability (traces · metrics · logs · alerts)
- [SigNoz MCP Server](https://signoz.io/docs/ai/signoz-mcp-server/) — AI assistant access to SigNoz data
- [OpenTelemetry](https://opentelemetry.io) — Vendor-neutral instrumentation
- [Anthropic Claude](https://anthropic.com) — Cost Guard reasoning engine
- [AWS EC2](https://aws.amazon.com/ec2/) — Deployment infrastructure

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

*Built for the [Agents of SigNoz Hackathon](https://www.wemakedevs.org/hackathons/signoz), July 2026.*
