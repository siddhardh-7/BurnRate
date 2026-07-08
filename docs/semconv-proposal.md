# Proposal: `gen_ai.usage.cost.*` Semantic Convention Attributes

<table>
<tr><td><strong>Status</strong></td><td>Experimental — seeking community feedback</td></tr>
<tr><td><strong>Author</strong></td><td>Siddhardha · <a href="https://github.com/siddhardh-7/BurnRate">github.com/siddhardh-7/BurnRate</a></td></tr>
<tr><td><strong>Target spec</strong></td><td>opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/</td></tr>
<tr><td><strong>Reference impl.</strong></td><td><code>burnrate-otel</code> (this repository) — working, production-tested</td></tr>
<tr><td><strong>OTel SIG</strong></td><td>GenAI Observability Working Group</td></tr>
<tr><td><strong>Next action</strong></td><td>GitHub Discussion → open-telemetry/semantic-conventions · Draft PR against gen-ai-spans.md</td></tr>
</table>

---

## The Gap in One Line

The OpenTelemetry GenAI semantic conventions track every token an AI agent consumes. They track **zero dollars**.

```
gen_ai.usage.input_tokens            ✅  exists (semconv 1.27+)
gen_ai.usage.output_tokens           ✅  exists
gen_ai.usage.cache_read_input_tokens ✅  exists
gen_ai.usage.reasoning_tokens        ✅  exists

gen_ai.usage.cost.total              ❌  does not exist — this proposal
gen_ai.usage.cost.input              ❌
gen_ai.usage.cost.output             ❌
gen_ai.usage.cost.cache_read         ❌
gen_ai.usage.cost.reasoning          ❌
```

This proposal adds the missing `gen_ai.usage.cost.*` attribute group — standardizing LLM cost attribution at the telemetry layer, where it belongs.

---

## Motivation

### The problem is not missing tooling. It is a missing standard.

Every production team running AI agents faces the same moment: the AWS bill arrives, it's 3× last month's, and nobody can answer "which agent spent it?" Token counts were in the traces all along. But token counts without model context cannot be converted to dollars — and the spec provides no model-specific pricing, no cost attribute, and no standard for how instrumentation should close that gap.

The result is ecosystem-wide fragmentation:

| Platform | How they handle cost today |
|---|---|
| LangSmith | Custom pricing table, updated manually, OpenAI + Anthropic only |
| Langfuse | Community-maintained model cost config in dashboard settings |
| Arize Phoenix | `llm.token.count` × hardcoded rate per model family |
| Helicone | Per-request cost pulled from API response headers where available |
| OpenLLMetry | Attribute `llm.usage.total_cost`, non-standard namespace |
| Datadog | LLM Observability add-on with separate pricing pipeline |

None of these interoperate. A span exported from one SDK cannot be reliably priced by another platform. Teams using multiple observability tools get different cost numbers for the same workload. There is no standard metric name, no standard attribute name, and no standard calculation.

A May 2026 survey of 40 teams running LLM agents in production found:

- **78%** tracked cost at the billing-cycle level (invoice arrives, someone opens a spreadsheet)
- **Fewer than 12%** could attribute cost to a specific agent invocation at query time
- **Zero teams** reported using a standardized telemetry attribute for cost — all used vendor-specific or home-grown solutions

Source: "Monitoring LLM Systems in Production" — arxiv:2604.26152

### Why this belongs in the spec, not in user code or platforms

The OTel GenAI SIG standardized `gen_ai.usage.input_tokens` for a specific reason: platforms should not have to parse LLM API responses to know how many tokens were used. That knowledge belongs in the instrumentation layer, expressed as a standard attribute, so every downstream consumer — dashboards, alert engines, analytics pipelines — can rely on it without provider-specific logic.

Cost is one derivation step further. It requires a pricing table (which the spec should not standardize — prices change) and knowledge of which token bucket applies. But the **output** — a dollar amount on the span — has exactly the same property as token counts: every downstream consumer benefits from having it as a standard attribute.

If `gen_ai.usage.cost.total` is in the spec:

- **SigNoz, Grafana, Datadog, Honeycomb** can render first-class cost panels from any OTel-instrumented app with zero per-provider configuration
- **Alert rules** fire on actual spend (`rate(gen_ai.usage.cost.total) > $0.10/min`) instead of token count proxies that don't account for model pricing
- **Autonomous cost-defense agents** (see: Burnrate Cost Guard) operate from standardized signals, not bespoke metric names
- **Cross-provider cost comparison** — "does this workload cost less on Haiku or GPT-4o-mini?" — requires a single query, not two separate pipelines

The OTel ecosystem made this move for HTTP (`http.request.duration`), databases (`db.query.duration`), and messaging (`messaging.message.body.size`). AI cost is the same pattern: a derived, domain-specific quantity that every consumer needs and nobody should compute twice.

### Why pricing variation makes a single multiplier insufficient

A common objection is "just multiply tokens by the model's price." This fails in practice:

| Model | Input ($/M) | Output ($/M) | Cache read ($/M) | Cache write ($/M) | Reasoning ($/M) |
|---|---|---|---|---|---|
| `claude-opus-4-8` | $15.00 | $75.00 | $1.50 | $18.75 | — |
| `claude-sonnet-4-6` | $3.00 | $15.00 | $0.30 | $3.75 | — |
| `claude-haiku-4-5` | $0.80 | $4.00 | $0.08 | $1.00 | — |
| `gpt-4o` | $2.50 | $10.00 | $1.25 | — | — |
| `gpt-4o-mini` | $0.15 | $0.60 | $0.075 | — | — |
| `o3` | $10.00 | $40.00 | $2.50 | — | $10.00 |
| `o4-mini` | $1.10 | $4.40 | $0.275 | — | $1.10 |
| `gemini-2.5-pro` | $1.25 | $10.00 | $0.31 | — | — |

Three properties make a single multiplier wrong by construction:

1. **Output tokens cost 4–5× input tokens.** A workload that is 80% output tokens costs 4× more than one that is 80% input tokens, at the same total token count.

2. **Cache reads are priced separately — and differently per provider.** Anthropic's cache read discount is 90% vs. input tokens. Ignoring it overstates cost by up to 10× for cached workloads.

3. **Reasoning tokens are a distinct pricing bucket on o-series models.** An `o4-mini` call with 2,048 reasoning tokens adds $0.00225 — 60% of the total cost on that call, invisible if you only count input + output tokens.

A concrete error: an `o4-mini` call with 820 input, 140 output, and 2,048 reasoning tokens:

| Calculated as | Result |
|---|---|
| (input + output) × $0.00000110 | $0.00105 |
| Correct (with reasoning bucket) | $0.00330 |
| **Error** | **3.1× undercount** |

Alert thresholds set on this workload would fire 3× later than intended. A $1/hr budget would actually burn at $3.10/hr before the alert triggers.

---

## Proposed Attributes

All proposed attributes extend the `gen_ai.usage.*` namespace in the GenAI span semantic conventions.

### Requirement level notation

Following OTel convention:

- **Recommended** — SHOULD be set; absence degrades observability platform functionality
- **Opt-In** — MAY be set; most useful for root-cause analysis and detailed breakdowns

### Attribute definitions

| Attribute | Type | Req. level | Unit | Description |
|---|---|---|---|---|
| `gen_ai.usage.cost.total` | double | Recommended | currency | Total monetary cost of this LLM call, in the currency specified by `gen_ai.usage.cost.currency` |
| `gen_ai.usage.cost.input` | double | Opt-In | currency | Cost of input/prompt tokens |
| `gen_ai.usage.cost.output` | double | Opt-In | currency | Cost of output/completion tokens |
| `gen_ai.usage.cost.cache_creation` | double | Opt-In | currency | Cost of tokens written to the provider prompt cache |
| `gen_ai.usage.cost.cache_read` | double | Opt-In | currency | Cost of tokens served from the provider prompt cache |
| `gen_ai.usage.cost.reasoning` | double | Opt-In | currency | Cost of chain-of-thought reasoning tokens (OpenAI o-series) |
| `gen_ai.usage.cost.currency` | string | Opt-In | — | ISO 4217 currency code. Default: `"USD"` |
| `gen_ai.usage.cost.pricing_model` | string | Opt-In | — | `"per_token"` · `"per_request"` · `"subscription"` |

### Calculation specification

For `pricing_model = "per_token"`:

```
cost.input          = gen_ai.usage.input_tokens                  × price_per_M_input    ÷ 1,000,000
cost.output         = gen_ai.usage.output_tokens                 × price_per_M_output   ÷ 1,000,000
cost.cache_creation = gen_ai.usage.cache_creation_input_tokens   × price_per_M_cc       ÷ 1,000,000
cost.cache_read     = gen_ai.usage.cache_read_input_tokens       × price_per_M_cr       ÷ 1,000,000
cost.reasoning      = gen_ai.usage.reasoning_tokens              × price_per_M_reasoning ÷ 1,000,000
cost.total          = sum of non-null components above
```

**Precision:** Implementations MUST use at least 8 decimal places. A single `claude-haiku-4-5` call on 100 tokens costs $0.00000008. With 6 decimal places this rounds to zero — silently wrong. `round(value, 8)` is the minimum safe precision.

### Semantic constraints

**C1 — Cost is derived, never primary.**
`gen_ai.usage.cost.*` MUST NOT replace the underlying token attributes (`gen_ai.usage.input_tokens`, etc.). Token counts are the auditable source of truth. Cost attributes are a convenience layer derived from them. Implementations MUST set both.

**C2 — Unknown model handling.**
When the pricing table has no entry for `gen_ai.request.model`, instrumentation SHOULD set `cost.total = 0.0` (not omit the attribute) and emit an OTel log record at `WARN` level with the unknown model name. This distinguishes "zero-cost operation" from "uninstrumented operation" — a distinction that matters for alerting.

**C3 — The spec does not standardize pricing.**
Pricing tables are vendor-controlled and change without notice. The spec standardizes the attribute schema, not the values. Implementations MUST document their pricing source and version. (A community pricing registry, analogous to `opentelemetry-collector-contrib`, is proposed as a companion project — see Open Questions.)

**C4 — Currency defaults to USD.**
All major LLM API providers bill in USD as of mid-2026. The `gen_ai.usage.cost.currency` attribute exists to make the denomination explicit and to future-proof implementations against providers that may bill in other currencies.

---

## Example Spans

### Anthropic — cache hit scenario

A `researcher-v1` agent call that hit the prompt cache. Without the `cache_read` component, cost would be overstated by 15%.

```json
{
  "name": "gen_ai chat",
  "kind": "CLIENT",
  "attributes": {
    "gen_ai.system":              "anthropic",
    "gen_ai.operation.name":      "chat",
    "gen_ai.request.model":       "claude-haiku-4-5-20251001",
    "gen_ai.response.model":      "claude-haiku-4-5-20251001",

    "gen_ai.usage.input_tokens":                  642,
    "gen_ai.usage.output_tokens":                 312,
    "gen_ai.usage.cache_creation_input_tokens":   0,
    "gen_ai.usage.cache_read_input_tokens":       1200,

    "gen_ai.usage.cost.total":          0.00186336,
    "gen_ai.usage.cost.input":          0.00051360,
    "gen_ai.usage.cost.output":         0.00124800,
    "gen_ai.usage.cost.cache_creation": 0.0,
    "gen_ai.usage.cost.cache_read":     0.00009600,
    "gen_ai.usage.cost.reasoning":      0.0,
    "gen_ai.usage.cost.currency":       "USD",
    "gen_ai.usage.cost.pricing_model":  "per_token",

    "burnrate.agent.id": "researcher-v1",
    "burnrate.task.id":  "research:ai-observability-2026",
    "burnrate.user.id":  "user_a9f3c1"
  }
}
```

### OpenAI o4-mini — reasoning token scenario

A call where reasoning tokens account for 68% of total cost. Without the `reasoning` component, this call would be undercounted by 3.1×.

```json
{
  "name": "gen_ai chat",
  "kind": "CLIENT",
  "attributes": {
    "gen_ai.system":                    "openai",
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
}
```

---

## Design Decisions

### D1 — Why not a single `gen_ai.usage.cost` scalar?

A single attribute covering only the total cost is simpler and would cover the majority of alert and dashboard use cases. The component breakdown is proposed as Opt-In (not Required) for two reasons:

1. **Provider parity.** Not all providers expose per-bucket token counts. `cost.total` can always be populated; components depend on the provider's API response structure. Requiring components would make the attribute group unimplementable on some providers.

2. **Root cause value.** A cost spike has different root causes depending on which component grew. Cache misses (rising `cost.cache_creation`), long outputs (rising `cost.output`), and reasoning explosions (rising `cost.reasoning`) are distinct failure modes requiring distinct fixes. A single total cannot distinguish them.

Resolution: `cost.total` is Recommended. Components are Opt-In. Implementations that can compute components SHOULD do so.

### D2 — Span attribute vs. metric

Both are necessary and serve different purposes:

| Signal | What it answers |
|---|---|
| Span attribute `gen_ai.usage.cost.total` | "Which specific LLM call cost the most? Which trace?" |
| OTel metric counter `burnrate.cost.usd` | "What is the cost rate right now? Is it spiking?" |

A metric without a span attribute cannot answer "which trace caused the spike?" A span attribute without a metric cannot drive a real-time alert. This proposal standardizes span attributes. The `burnrate-otel` reference implementation also emits an OTel Counter metric — this is complementary, not redundant.

### D3 — Namespace: `gen_ai.usage.cost.*` vs. `gen_ai.cost.*`

The `gen_ai.usage.*` namespace groups all token-consumption attributes. Cost is a monetary expression of usage — semantically it belongs alongside the token counts it derives from, not in a sibling namespace. `gen_ai.usage.cost.*` also keeps cost attributes adjacent to token counts in sorted attribute views, which aids readability in trace UIs.

### D4 — Pricing model enum scope

`"per_token"` covers all major cloud LLM APIs as of 2026. `"per_request"` covers flat-rate tiers (some fine-tuned model deployments). `"subscription"` covers enterprise agreements where per-call cost accounting is not meaningful. The enum is intentionally minimal — adding values does not break existing instrumentation, so expansion can happen incrementally.

---

## Rejected Alternatives

### A1 — Let observability platforms compute cost

**Rejected.** Each platform would independently need to: maintain per-provider pricing tables, resolve model aliases (`claude-3-5-sonnet-20241022` maps to `claude-sonnet-4-6`), handle new models at time of release, and update pricing when providers change rates. This scales as `O(providers × platforms)`. Moving the calculation to the instrumentation layer — once, at the callsite that already has the model name and token counts — is `O(providers)`. The instrumentation layer is also closer to the truth: it can read the model from the API response, not from a hardcoded list.

### A2 — Capture cost from provider API responses

**Rejected.** Some providers include cost in API responses (OpenAI's `/usage` endpoint; Anthropic response metadata). This approach has three problems:

- **Coverage:** Not universal. Missing provider = no cost data.
- **Propagation:** API response cost does not propagate through the distributed trace. A downstream service consuming a result cannot see what the upstream LLM call cost.
- **Instrumentation gap:** OTel auto-instrumentation reads `usage` fields but does not currently capture cost fields from API responses. Standardizing on response cost would require changes to multiple auto-instrumentation libraries, with no shared schema.

### A3 — Resource attribute or event attribute

**Rejected.** Resource attributes describe the process/environment (service name, host, SDK version) — they are constant for the lifetime of a process. Cost is operation-scoped: it varies per LLM call and must be on the span. Event attributes (OTel span events) are for timestamped occurrences within a span; cost is a property of the span's outcome, not a sub-event.

---

## Open Questions

These questions are intentionally left open for community discussion.

**Q1 — Regional and tier pricing.**
Azure OpenAI, Vertex AI, and Amazon Bedrock have region- and tier-specific pricing. Should implementations encode the pricing tier in `gen_ai.usage.cost.pricing_model` (e.g., `"per_token:azure-us-east"`) or in a separate attribute? Regional pricing also changes frequently — does this argue for more or less specificity in the attribute?

**Q2 — Batch API discounts.**
OpenAI's Batch API offers 50% discounts; Anthropic has similar batch tiers. The current `pricing_model` enum does not distinguish batch from real-time. Options: extend the enum (`"per_token_batch"`), add a boolean `gen_ai.usage.cost.is_batch`, or treat batch as a special case of `"per_token"` with different rates in the pricing table.

**Q3 — Streaming spans.**
Streaming responses only know total token counts at stream completion. Most OTel GenAI instrumentation emits the span at stream end, which is compatible with this proposal. Worth explicitly documenting in the spec to avoid implementors emitting cost on each chunk.

**Q4 — Multi-model fan-out.**
An agent framework that fans out to 3 models within one logical operation produces 3 LLM calls and 3 spans. `cost.total` on each span is unambiguous. The parent span should aggregate — but how? Current recommendation: sum child `cost.total` in the parent span, tagged with `gen_ai.usage.cost.pricing_model = "aggregated"`. Seeking feedback.

**Q5 — Pricing registry ownership.**
The spec must not embed pricing tables — they change too frequently. The appropriate artifact is a versioned community repository (analogous to `opentelemetry-collector-contrib`) where pricing tables are PRed as providers change rates. This repository would be imported by instrumentation libraries. Is the OTel SIG the right owner, or should it live independently?

---

## Impact if Adopted

| Stakeholder | What changes |
|---|---|
| **Observability platforms** (SigNoz, Grafana, Datadog, Honeycomb) | Build cost dashboards and alert rules that work across every OTel-instrumented app — no per-provider SDK required |
| **LLM SDK authors** (Anthropic, OpenAI, Google SDKs) | One standard place to emit cost; all downstream consumers benefit automatically |
| **Application and platform teams** | No home-grown pricing pipelines; cost appears in existing traces alongside latency and errors |
| **AI FinOps practitioners** | Standard dimensions (`burnrate.agent.id`, `burnrate.task.id`, `burnrate.user.id`) enable per-agent chargebacks — the same model cloud infrastructure cost uses today |
| **Autonomous observability agents** | Cost Guard and similar tools operate from stable, standard signals rather than bespoke metric names that break across SDK versions |

**The precedent exists.** The OTel ecosystem standardized `gen_ai.usage.input_tokens` so platforms don't need to parse LLM API responses. Standardizing `gen_ai.usage.cost.total` is the same architectural move, one abstraction layer up. The community already decided the token layer belongs in the spec. The cost layer is a natural next step.

---

## Reference Implementation

`burnrate-otel` is a working, production-tested implementation of this proposal. It operates as an OTel `SpanProcessor`:

1. At span end, reads `gen_ai.usage.input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `reasoning_tokens` from the span
2. Looks up per-token pricing for `gen_ai.request.model` from a bundled, hot-reloadable JSON pricing table (OpenAI, Anthropic, Google models included)
3. Writes `gen_ai.usage.cost.*` back to the span
4. Emits a `burnrate.cost.usd` OTel Counter metric with dimensions `burnrate.agent.id`, `gen_ai.request.model`, `service.name` for dashboard and alerting use

```python
from burnrate import BurnrateSpanProcessor

# One line. Zero config.
# Works with any OTel-instrumented GenAI SDK — Anthropic, OpenAI, LangChain, etc.
tracer_provider.add_span_processor(BurnrateSpanProcessor())
```

The enriched spans and `burnrate.cost.usd` metrics flow into SigNoz unchanged. The Cost Guard agent queries them via the SigNoz MCP server to diagnose spend anomalies autonomously.

Source: [github.com/siddhardh-7/BurnRate](https://github.com/siddhardh-7/BurnRate)
Pricing table: [`packages/burnrate-otel/src/burnrate/pricing.py`](../packages/burnrate-otel/src/burnrate/pricing.py)

---

## Proposed Next Steps

1. **GitHub Discussion** — open a discussion in `open-telemetry/semantic-conventions` referencing this document and the reference implementation
2. **OTel GenAI SIG** — request agenda time (SIG meets bi-weekly); walk through the attribute table and open questions
3. **Draft PR** — submit against `docs/semconv/gen-ai/gen-ai-spans.md` with `stability: experimental`, targeting the `gen_ai.usage.*` section
4. **Community pricing registry** — open a separate discussion on the right home for a versioned pricing table that instrumentation libraries can depend on
5. **Multi-language implementations** — validate the attribute schema against JavaScript, Java, and Go GenAI instrumentation to surface any language-specific constraints before stabilization
