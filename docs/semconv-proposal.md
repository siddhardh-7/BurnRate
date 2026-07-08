# Proposal: `gen_ai.usage.cost.*` Semantic Convention Attributes

**Status:** Proposal  
**Author:** Burnrate (Agents of SigNoz Hackathon, July 2026)  
**Upstream reference:** https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/

---

## Problem

The OpenTelemetry GenAI semantic conventions define token-usage attributes:

| Attribute | Type | Description |
|---|---|---|
| `gen_ai.usage.input_tokens` | int | Tokens in the input/prompt |
| `gen_ai.usage.output_tokens` | int | Tokens in the response |
| `gen_ai.usage.cache_creation_input_tokens` | int | Tokens used for cache creation |
| `gen_ai.usage.cache_read_input_tokens` | int | Tokens read from cache |
| `gen_ai.usage.reasoning_tokens` | int | Chain-of-thought tokens (o-series) |

**There is no cost attribute.** Token counts without model context cannot be converted to dollars by observability platforms. Every team that wants cost visibility must implement model-specific cost calculation outside the tracing layer — duplicating work, creating inconsistency, and missing multi-model/multi-provider cost attribution entirely.

This is not a hypothetical gap. Multiple production teams have raised this:
- LangSmith, Langfuse, Arize Phoenix, and Helicone all implement custom cost attribution — none standardized.
- AI FinOps is a recognized emerging discipline with no standard telemetry foundation.
- The April 2026 survey "Monitoring LLM Systems" (arxiv:2604.26152) identifies cost-behavior correlation as an unsolved observability problem.

---

## Proposed Attributes

All attributes below are proposed for addition to the GenAI span semantic conventions:

| Attribute | Type | Required | Description |
|---|---|---|---|
| `gen_ai.usage.cost.total` | double | Recommended | Total cost in `gen_ai.usage.cost.currency` units |
| `gen_ai.usage.cost.input` | double | Optional | Cost of input/prompt tokens |
| `gen_ai.usage.cost.output` | double | Optional | Cost of output/completion tokens |
| `gen_ai.usage.cost.cache_creation` | double | Optional | Cost of cache write tokens (Anthropic) |
| `gen_ai.usage.cost.cache_read` | double | Optional | Cost of cache-hit read tokens |
| `gen_ai.usage.cost.reasoning` | double | Optional | Cost of chain-of-thought reasoning tokens (OpenAI o-series) |
| `gen_ai.usage.cost.currency` | string | Optional | ISO 4217 currency code, default `"USD"` |
| `gen_ai.usage.cost.pricing_model` | string | Optional | `"per_token"` \| `"per_request"` \| `"subscription"` |

### Notes

1. **Precision:** Values should use at least 6 decimal places to represent sub-cent operations accurately. `round(cost, 8)` is recommended.
2. **Unknown models:** Instrumentation libraries SHOULD set cost to `0.0` and emit a log record rather than omitting the attribute, to distinguish "zero cost" from "not instrumented."
3. **Currency:** Defaults to USD, the denomination used by all major LLM providers as of 2026.
4. **Relationship to token attrs:** `gen_ai.usage.cost.*` are derived values. Implementations MUST NOT omit the underlying token attributes — they are the source of truth for auditability.
5. **Pricing table:** The spec does not define a pricing table. Implementors supply pricing; the `burnrate-otel` library ships a community-maintained table. The `gen_ai.usage.cost.pricing_model` attribute documents the method used.

---

## Example Span (After Enrichment)

```json
{
  "name": "gen_ai chat",
  "attributes": {
    "gen_ai.system": "anthropic",
    "gen_ai.operation.name": "chat",
    "gen_ai.request.model": "claude-haiku-4-5-20251001",
    "gen_ai.response.model": "claude-haiku-4-5-20251001",
    "gen_ai.usage.input_tokens": 1842,
    "gen_ai.usage.output_tokens": 312,
    "gen_ai.usage.cache_creation_input_tokens": 0,
    "gen_ai.usage.cache_read_input_tokens": 1200,
    "gen_ai.usage.cost.total": 0.00220576,
    "gen_ai.usage.cost.input": 0.00147360,
    "gen_ai.usage.cost.output": 0.00124800,
    "gen_ai.usage.cost.cache_read": 0.00009600,
    "gen_ai.usage.cost.currency": "USD",
    "gen_ai.usage.cost.pricing_model": "per_token",
    "burnrate.agent.id": "researcher-v1",
    "burnrate.task.id": "research:ai-observability-trends",
    "burnrate.user.id": "user_abc123"
  }
}
```

---

## Impact

Standardizing `gen_ai.usage.cost.*` enables:

1. **Platform-side cost dashboards** — SigNoz, Grafana, Datadog, and Honeycomb can build first-class cost views without custom configuration per provider.
2. **Cost-based alerting** — budget alerts based on spend attribution, not just token counts.
3. **Cross-provider benchmarking** — compare cost efficiency across OpenAI, Anthropic, Google models on the same task.
4. **FinOps for AI agents** — the `burnrate.agent.id`, `burnrate.task.id`, `burnrate.user.id` dimension pattern enables AI cost chargebacks, the same way cloud infrastructure cost is attributed today.
5. **Autonomous cost defense** — agents like Burnrate Cost Guard can react to cost signals in real time, using observability data that follows a standard format.

---

## Reference Implementation

This proposal is implemented in [`burnrate-otel`](https://github.com/yourusername/burnrate), an OTel SpanProcessor that enriches any GenAI span with cost attributes and emits `burnrate.cost.usd` metrics into SigNoz — zero config required.

```python
from burnrate import BurnrateSpanProcessor
provider.add_span_processor(BurnrateSpanProcessor())
```
