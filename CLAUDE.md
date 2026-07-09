# Burnrate — Project Context

FinOps toolkit for AI agents, built for the Agents of SigNoz hackathon (July 2026).
Three deliverables: an OTel SDK that enriches GenAI spans with dollar costs, a
Cost Guard agent that auto-diagnoses spend spikes via the SigNoz MCP server, and
a chaos-injectable demo app. Plus a formal OTel semconv proposal
(`docs/semconv-proposal.md`) — treat it as a first-class deliverable, not docs.

## Layout

```
packages/burnrate-otel/   SDK: SpanProcessor + pricing table + cost metrics (core deliverable)
cost-guard/               FastAPI webhook → Claude + SigNoz MCP investigation → throttle action
demo-app/                 Multi-agent pipeline (researcher-v1, summarizer-v1) + chaos injection
dashboards/               SigNoz dashboard JSONs (v5 widget format)
alerts/                   SigNoz alert rule definitions
docs/                     semconv-proposal.md, demo-script.md
pours/                    foundryctl-generated self-hosted SigNoz deployment config — do not hand-edit
```

Each Python component is a separate uv project. Install/run with `uv`, not pip
(`pip` is not on PATH here). After editing cost-guard source, `uv pip install -e .`
from `cost-guard/` — it runs as an installed package and stale `.pyc` files have
bitten us before.

## Running locally

```bash
cd demo-app  && uv run python -m demo.app          # port 8001
cd cost-guard && uv run python -m guard.webhook    # port 8082
```

Self-hosted SigNoz (via foundryctl): UI :8080, MCP :8000 (`/mcp`), OTLP gRPC :4317, HTTP :4318.
Secrets live in `.env` at repo root (SIGNOZ_API_KEY, ANTHROPIC_API_KEY, COST_GUARD_MOCK).

## Constraints that are easy to break

- **MeterProvider before BurnrateSpanProcessor.** `CostMetrics` captures the global
  MeterProvider at processor init. Set it after, and all cost metrics silently go
  to the no-op provider. See the ordering comment in `demo-app/src/demo/app.py`.
- **Cost attributes are written in `_on_ending`, not `on_end`.** By `on_end` the
  span is read-only. The processor temporarily clears `BoundedAttributes._immutable`
  (OTel SDK 1.43 internal API) to write `gen_ai.usage.cost.*` — fragile across SDK
  upgrades; failures are swallowed so metrics still flow.
- **SigNoz webhook URL must be `http://host.docker.internal:8082/alert`**, never
  `localhost` — SigNoz runs in Docker; localhost resolves inside the container.
- **SigNoz alert payloads use `status` (not `state`) and wrap alerts in an
  `alerts[]` array.** Parsing lives in `cost-guard/src/guard/webhook.py`.
- **Dashboard JSON is SigNoz v5 `widgets` + `layout` format.** A bare `layout`
  array with inline panels imports as an empty dashboard. Table-panel `orderBy`
  must use `__result`, not `value`. Push updates via
  `PUT /api/v1/dashboards/{id}` with the `SIGNOZ-API-KEY` header.
- **Mock mode:** `_MOCK_MODE = True` is hardcoded in
  `cost-guard/src/guard/investigate.py` (Anthropic credits were unavailable);
  `.env` has `COST_GUARD_MOCK=true` but the env var is not yet wired up. Wire it
  before real-mode demos. In real mode, MCP tools are filtered from 41 to 8 and
  tool results truncated to 2000 chars to stay under the 10k tokens/min rate limit.

## Key names

- Metric: `burnrate.cost.usd`, dimensions `burnrate.agent.id`, `gen_ai.request.model`, `service.name`
- Span attrs (proposed semconv): `gen_ai.usage.cost.{total,input,output,cache_creation,cache_read,reasoning,currency,pricing_model}`
- All attribute/metric name constants live in `packages/burnrate-otel/src/burnrate/semconv.py`

## Chaos / E2E loop

```bash
curl -X POST http://localhost:8001/chaos/activate/retry_loop   # also: model_misroute, prompt_bloat, cache_miss_storm
curl -X POST "http://localhost:8001/research/batch?count=5"    # generate traffic
# SigNoz alert (BurnRateBudgetAlert, ~60-90s) → Cost Guard → throttles researcher-v1
curl -X POST http://localhost:8001/control/restore             # clear throttles after testing
curl -X POST http://localhost:8001/chaos/deactivate
```

Full recording script with pre-flight checklist: `docs/demo-script.md`.

## Project memory

`memory/` (gitignored — internal notes, never commit) holds session-persistent
state: `MEMORY.md` is the index; read it at session start. `debugging-history.md`
maps symptoms to already-fixed root causes — check it before re-debugging anything.

## Conventions

- Do not add `Co-Authored-By: Claude` to commits in this repo (history was
  rewritten once to remove it).
- README and semconv-proposal are polished for judges — keep edits in that voice.
