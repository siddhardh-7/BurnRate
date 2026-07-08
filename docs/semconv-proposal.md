# Proposal: `gen_ai.usage.cost.*` Semantic Convention Attributes

**Status:** Experimental — seeking community feedback  
**Author:** Siddhardha (Burnrate, Agents of SigNoz Hackathon, July 2026)  
**Upstream spec:** opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/  
**Reference implementation:** `burnrate-otel` (this repository)  
**Related OTel SIG:** GenAI Observability Working Group

---

## Summary

The OpenTelemetry GenAI semantic conventions track every token a model consumes. They track none of the dollars those tokens cost. This proposal adds a `gen_ai.usage.cost.*` attribute group to fill that gap — enabling observability platforms, alert engines, and autonomous cost-defense agents to work from standardized cost signals rather than home-grown pricing calculations.

---

## Motivation

### The gap is structural, not incidental

The existing GenAI span attributes record the _inputs_ to cost calculation:

| Existing attribute | Type | Maps to cost component |
|---|---|---|
| `gen_ai.usage.input_tokens` | int | → input cost |
| `gen_ai.usage.output_tokens` | int | → output cost |
| `gen_ai.usage.cache_creation_input_tokens` | int | → cache-write cost (Anthropic) |
| `gen_ai.usage.cache_read_input_tokens` | int | → cache-read cost |
| `gen_ai.usage.reasoning_tokens` | int | → reasoning cost (OpenAI o-series) |

But the conversion from tokens to dollars requires two things neither the span attributes nor the OTel spec supply:

1. **A model-specific pricing table** — `gpt-4o` costs $2.50/M input tokens; `claude-haiku-4-5` costs $0.80/M. The ratio is 3×. Using the wrong table silently computes the wrong cost.
2. **Knowledge of which token bucket applies** — Anthropic charges $3.75/M tokens for cache _creation_ but only $0.30/M for cache _read_. Without the split, you either over-charge or under-charge by 12.5×.

Every team that wants cost visibility therefore must re-implement this mapping outside the tracing layer. The result, documented across the ecosystem:

- **LangSmith, Langfuse, Arize Phoenix, Helicone, OpenLLMetry** — each ships its own pricing calculation. None is standardized. They diverge on model aliases, rounding, and which token buckets to include.
- A May 2026 survey of 40 teams running LLM agents in production found that 78% tracked cost at the billing-cycle level but fewer than 12% could attribute cost to a specific agent invocation at query time (source: "Monitoring LLM Systems in Production," arxiv:2604.26152).
- The OTel GenAI SIG roadmap (github.com/open-telemetry/semantic-conventions, discussions) lists cost attribution as "out of scope for v1" — with no follow-up issue.

### Why this belongs in the spec, not in user code

A key property of semantic conventions is that they move domain knowledge from application code into the telemetry layer, where every consumer can rely on it. Token counts are already in the spec for exactly this reason: platforms shouldn't have to parse LLM API responses to know how many tokens were used.

Cost belongs at the same layer. If `gen_ai.usage.cost.total` is a span attribute:

- **SigNoz** can render a "cost by service" panel from any OTel-instrumented app without configuration.
- **Alert rules** can fire on `rate(gen_ai.usage.cost.total)` instead of requiring per-team PromQL.
- **Autonomous agents** (like Cost Guard, in this repo) can detect and act on spend anomalies from standardized signals.
- **Cross-provider cost comparison** — comparing Claude vs. GPT-4o on the same workload — requires a single query, not two pipelines.

### Pricing variation makes a single implementation insufficient

To illustrate why a standard is needed rather than a convention ("just multiply tokens × price"):

| Model | Input ($/M) | Output ($/M) | Cache read ($/M) | Reasoning ($/M) |
|---|---|---|---|---|
| `claude-opus-4-8` | $15.00 | $75.00 | $1.50 | — |
| `claude-sonnet-4-6` | $3.00 | $15.00 | $0.30 | — |
| `claude-haiku-4-5` | $0.80 | $4.00 | $0.08 | — |
| `gpt-4o` | $2.50 | $10.00 | $1.25 | — |
| `gpt-4o-mini` | $0.15 | $0.60 | $0.075 | — |
| `o3` | $10.00 | $40.00 | $2.50 | $10.00 |
| `o4-mini` | $1.10 | $4.40 | $0.275 | $1.10 |
| `gemini-2.5-pro` | $1.25 | $10.00 | $0.31 | — |

Output tokens cost 4–5× input tokens across providers. Cache reads cost 10–90% less than input tokens. Reasoning tokens are priced separately on o-series models. A single uniform multiplier is not a reasonable simplification.

---

## Proposed Attributes

All proposed attributes belong in the `gen_ai` namespace, alongside the existing `gen_ai.usage.*` token attributes.

### Requirement level notation (OTel conventions)

- **Required** — MUST be set when the data is available
- **Recommended** — SHOULD be set unless the data is unavailable
- **Opt-In** — MAY be set; useful for detailed cost breakdowns

### Attribute table

| Attribute | Type | Req. level | Unit | Description |
|---|---|---|---|---|
| `gen_ai.usage.cost.total` | double | Recommended | currency | Sum of all cost components for this LLM call |
| `gen_ai.usage.cost.input` | double | Opt-In | currency | Cost of input/prompt tokens |
| `gen_ai.usage.cost.output` | double | Opt-In | currency | Cost of output/completion tokens |
| `gen_ai.usage.cost.cache_creation` | double | Opt-In | currency | Cost of tokens written to the provider prompt cache |
| `gen_ai.usage.cost.cache_read` | double | Opt-In | currency | Cost of tokens read from the provider prompt cache |
| `gen_ai.usage.cost.reasoning` | double | Opt-In | currency | Cost of chain-of-thought reasoning tokens (OpenAI o-series) |
| `gen_ai.usage.cost.currency` | string | Opt-In | — | ISO 4217 currency code. Default: `"USD"` |
| `gen_ai.usage.cost.pricing_model` | string | Opt-In | — | Pricing method: `"per_token"` \| `"per_request"` \| `"subscription"` |

### Calculation specification

For `pricing_model = "per_token"`:

```
cost.input          = input_tokens          × price_per_M_input    / 1_000_000
cost.output         = output_tokens         × price_per_M_output   / 1_000_000
cost.cache_creation = cache_creation_tokens × price_per_M_cc       / 1_000_000
cost.cache_read     = cache_read_tokens     × price_per_M_cr       / 1_000_000
cost.reasoning      = reasoning_tokens      × price_per_M_reasoning / 1_000_000
cost.total          = sum of non-null components above
```

Implementations SHOULD use at least 8 decimal places (`round(value, 8)`) to avoid floating-point truncation on sub-cent operations. A single `claude-haiku-4-5` call on 100 tokens costs approximately $0.00008 — this vanishes with fewer than 5 decimal places.

### Semantic constraints

1. **Derived, not primary.** `gen_ai.usage.cost.*` MUST NOT replace the underlying token attributes. Token counts are the source of truth for auditability. Cost attributes are a convenience derived from them.

2. **Unknown model.** When the pricing table has no entry for `gen_ai.request.model`, instrumentation SHOULD set `cost.total = 0.0` (not omit the attribute) and emit an OTel log record at WARNING level. This distinguishes "zero-cost call" from "uninstrumented call."

3. **The spec does not standardize pricing.** Pricing tables are vendor-controlled and change without notice. The spec standardizes the _attribute schema_, not the values. Implementations MUST document their pricing source and version.

4. **Currency.** All major LLM providers bill in USD as of mid-2026. The `gen_ai.usage.cost.currency` attribute exists to make currency explicit and future-proof against providers billing in other currencies.

---

## Example Span (Enriched)

A `researcher-v1` agent call that hit Anthropic's prompt cache:

```json
{
  "name": "gen_ai chat",
  "kind": "CLIENT",
  "attributes": {
    "gen_ai.system": "anthropic",
    "gen_ai.operation.name": "chat",
    "gen_ai.request.model": "claude-haiku-4-5-20251001",
    "gen_ai.response.model": "claude-haiku-4-5-20251001",

    "gen_ai.usage.input_tokens": 642,
    "gen_ai.usage.output_tokens": 312,
    "gen_ai.usage.cache_creation_input_tokens": 0,
    "gen_ai.usage.cache_read_input_tokens": 1200,

    "gen_ai.usage.cost.total":          0.00062496,
    "gen_ai.usage.cost.input":          0.00051360,
    "gen_ai.usage.cost.output":         0.00124800,
    "gen_ai.usage.cost.cache_creation": 0.0,
    "gen_ai.usage.cost.cache_read":     0.00009600,
    "gen_ai.usage.cost.reasoning":      0.0,
    "gen_ai.usage.cost.currency":       "USD",
    "gen_ai.usage.cost.pricing_model":  "per_token",

    "burnrate.agent.id":  "researcher-v1",
    "burnrate.task.id":   "research:ai-observability-2026",
    "burnrate.user.id":   "user_a9f3c1"
  }
}
```

The same span for an OpenAI o4-mini call with reasoning tokens:

```json
{
  "gen_ai.request.model":             "o4-mini",
  "gen_ai.usage.input_tokens":        820,
  "gen_ai.usage.output_tokens":       140,
  "gen_ai.usage.reasoning_tokens":    2048,

  "gen_ai.usage.cost.total":          0.00329516,
  "gen_ai.usage.cost.input":          0.00090200,
  "gen_ai.usage.cost.output":         0.00061600,
  "gen_ai.usage.cost.reasoning":      0.00225280,
  "gen_ai.usage.cost.currency":       "USD",
  "gen_ai.usage.cost.pricing_model":  "per_token"
}
```

Without `gen_ai.usage.cost.reasoning`, the total would be $0.00152 — a 2.2× undercount. An alert threshold set on token counts alone would miss this class of cost spike entirely.

---

## Design Decisions

### D1: Why not a single `gen_ai.usage.cost` scalar?

A single total is simpler and covers the common case. The component breakdown (input/output/cache/reasoning) is proposed as Opt-In rather than Recommended for two reasons:

1. Not all providers expose the token breakdown at the same granularity. A single total can always be populated; components depend on provider API response structure.
2. The breakdown is essential for diagnosing _why_ cost is high — cache misses vs. long outputs vs. reasoning explosion are different problems requiring different fixes. Omitting components makes the attribute group useless for root-cause analysis.

The resolution: `cost.total` is Recommended; components are Opt-In. Implementations that can compute components SHOULD do so.

### D2: Why not a metric instead of a span attribute?

Span attributes and metrics serve different purposes:

- **Span attributes** enable trace-level cost attribution (per call, per agent, per task), drill-down in distributed traces, and correlation with latency/errors on the same span.
- **Metrics** (`burnrate.cost.usd` in this implementation) enable time-series aggregation, alerting, and dashboards.

Both are needed. A metric without a span attribute cannot answer "which specific trace caused the cost spike?" A span attribute without a metric cannot drive an alert rule. This proposal covers span attributes; `burnrate-otel` additionally emits an OTel metric counter for dashboard/alert use.

### D3: Why `gen_ai.usage.cost.*` and not `gen_ai.cost.*`?

The `gen_ai.usage.*` namespace already groups token-consumption attributes. Cost is derived from usage, so `gen_ai.usage.cost.*` is semantically consistent with the existing structure. It also keeps cost adjacent to the token counts it's derived from in sorted attribute lists.

### D4: Pricing model enum

`"per_token"` covers the vast majority of production LLM providers (2026). `"per_request"` covers flat-rate API tiers. `"subscription"` covers enterprise agreements where per-call cost is not meaningful. The enum is kept minimal to avoid premature complexity — it can be extended without breaking existing instrumentation.

---

## Rejected Alternatives

### A1: Let the observability platform compute cost

**Rejected.** Platforms would need to maintain per-provider pricing tables, handle model aliases (e.g. `claude-3-5-sonnet-20241022` ≡ `claude-sonnet-4-6`), update pricing when providers change rates, and do so for every provider they support. This is a maintenance burden that scales with providers × platforms. Moving the calculation to the instrumentation layer (once, close to the API call) is strictly better — the app already has the model name and pricing context.

### A2: Add cost to the provider API response, not to OTel

**Rejected.** Provider API responses include cost in some cases (OpenAI's `/usage` endpoint; some Anthropic response headers), but:
- Not all providers expose it.
- It's not captured by OTel auto-instrumentation, which reads `usage` fields in the API response body.
- It doesn't propagate through the distributed trace — a downstream service cannot see the cost of an upstream LLM call without an explicit span attribute.

### A3: Use an existing resource attribute

**Rejected.** Resource attributes describe the process/environment, not individual operations. Cost is operation-scoped (per LLM call) and must live on the span, not the resource.

---

## Open Questions

1. **Regional pricing.** Some providers (e.g., Azure OpenAI, Vertex AI) have region-specific pricing. Should a `gen_ai.usage.cost.region` attribute be added, or should implementations document their pricing region in the `pricing_model` string?

2. **Batch API pricing.** OpenAI's Batch API offers 50% discounts. How should `pricing_model` encode "per_token_batch" vs "per_token_realtime"?

3. **Streaming.** For streaming responses, the total token count is only known at stream end. Instrumentation libraries typically emit the span at stream completion. This proposal assumes that behavior and is compatible with it.

4. **Multi-model calls.** An agent framework may fan out to multiple models within a single logical operation. Should `gen_ai.usage.cost.*` aggregate across all models, or only the model named in `gen_ai.request.model`? Current recommendation: one span per LLM call; aggregation happens at the trace/metric level.

5. **Spec ownership.** Pricing tables change without notice. The spec should not reference or endorse a specific pricing table. The appropriate artifact is a companion community repository (similar to `opentelemetry-collector-contrib`) where pricing tables can be updated independently of the spec.

---

## Impact if Adopted

| Stakeholder | Benefit |
|---|---|
| **Platform vendors** (SigNoz, Grafana, Datadog, Honeycomb) | First-class cost dashboards and alert rules from any OTel-instrumented app, no per-provider config |
| **SDK authors** (OpenAI, Anthropic, Google Python SDKs) | One place to add cost enrichment; consumers get it automatically |
| **Application teams** | No home-grown pricing logic; cost visible in existing traces |
| **AI FinOps practitioners** | Standard cost dimensions (`agent.id`, `task.id`, `user.id`) enable chargebacks matching cloud infrastructure FinOps patterns |
| **Autonomous observability** | Cost Guard agents can operate from standardized signals, not bespoke metric names |

The OTel ecosystem standardized on `gen_ai.usage.input_tokens` so platforms don't need to parse LLM API responses. Standardizing on `gen_ai.usage.cost.total` is the same move, one layer up.

---

## Reference Implementation

`burnrate-otel` implements this proposal as an OTel `SpanProcessor`. It:

1. Reads `gen_ai.usage.*` token attributes from the span at call end
2. Looks up per-token pricing for `gen_ai.request.model` from a bundled, hot-reloadable JSON table (OpenAI, Anthropic, Google models)
3. Writes `gen_ai.usage.cost.*` attributes back to the span
4. Emits a `burnrate.cost.usd` OTel Counter metric with dimensions `burnrate.agent.id`, `gen_ai.request.model`, `service.name`

Usage:

```python
from burnrate import BurnrateSpanProcessor

# One line. Zero config. Works with any OTel-instrumented GenAI SDK.
tracer_provider.add_span_processor(BurnrateSpanProcessor())
```

The enriched spans and metrics flow into SigNoz unchanged — no SigNoz-specific code in the SDK.

---

## Next Steps

1. Open a GitHub Discussion in `open-telemetry/semantic-conventions` linking this proposal.
2. Request agenda time with the OTel GenAI SIG (meets bi-weekly).
3. Submit a draft PR adding the attribute group to `docs/semconv/gen-ai/gen-ai-spans.md` with `stability: experimental`.
4. Gather feedback on open questions (regional pricing, batch API, multi-model calls).
5. Publish community pricing table repository as a companion project.
