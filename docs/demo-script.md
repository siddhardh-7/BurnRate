# 3-Minute Demo Script

## Setup (before recording)

- Demo app running on port 8001: `cd demo-app && uv run python -m demo.app`
- Cost Guard running on port 8082: `cd cost-guard && uv run python -m guard.webhook`
- SigNoz "Burn Rate Live" dashboard open, burn rate showing baseline traffic
- Terminal 2: Cost Guard logs tailing: `docker compose logs -f cost-guard`
  (or `tail -f /tmp/cost-guard.log` for local run)
- Terminal 3: ready for chaos injection commands
- Slack open on side showing no alerts
- SigNoz notification channel configured to `http://host.docker.internal:8082/alert`

---

## Script

### [0:00–0:20] The Hook

**Narrate over the OTel GenAI spec page:**

> "The OpenTelemetry GenAI semantic conventions track everything about your AI agents. Every input token. Every output token. Cache hits. Reasoning tokens. Everything — except a single dollar. There's no cost attribute in the spec. So when your agent runs wild at 3am, your observability platform tells you *how many tokens* it burned. Not *how much money* you lost."

**Show:** opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/ — the `gen_ai.usage.*` table with no cost row.

---

### [0:20–0:45] Normal State

**Narrate while showing SigNoz "Burn Rate Live" dashboard:**

> "This is Burnrate. One line of code added to our agent system — `provider.add_span_processor(BurnrateSpanProcessor())` — and SigNoz now sees real dollar costs. Every span carries `gen_ai.usage.cost.total`. Every agent's spend flows into these metrics. Right now we're burning about 14 cents an hour. Normal."

**Show:** Clean dashboard, modest burn rate line, cost-by-agent panel showing both agents (researcher, summarizer) with low steady values.

---

### [0:45–1:00] Inject Chaos

**Run in terminal (demo app is on port 8001):**
```bash
curl -X POST http://localhost:8001/chaos/activate/retry_loop
# Then fire 10 concurrent requests:
for i in $(seq 1 10); do curl -s -X POST "http://localhost:8001/research?topic=AI+observability" & done; wait
```

**Narrate:**
> "Let's inject a bug. The researcher agent now has a broken error handler — it retries every LLM call 8 to 12 times before giving up. Each retry grows the context. Watch the burn rate."

**Show:** The burn rate line on SigNoz goes from flat → near-vertical. $0.14/hr → $5.80/hr in 60 seconds.

---

### [1:00–1:30] Cost Guard Activates

**Narrate while watching Cost Guard logs:**
> "Our SigNoz budget alert just fired. Cost Guard wakes up. It's using the official SigNoz MCP server to investigate — querying traces to find the culprit agent, checking metrics to quantify the blast radius, scanning logs for error patterns."

**Show:** Cost Guard logs showing:
```
INFO  Alert received: BurnRateBudgetAlert  status=firing
INFO  Investigating alert='BurnRateBudgetAlert' service='burnrate-demo-app'
INFO  [SigNoz MCP] signoz_query_metrics → burnrate.cost.usd by agent: researcher-v1=5.8/hr
INFO  [SigNoz MCP] signoz_search_traces → 47 spans from researcher-v1 in last 10min
INFO  Diagnosis: culprit=researcher-v1 confidence=high cost=10.98/hr
INFO  ACTION: throttled agent=researcher-v1 to 2 calls/min
```

---

### [1:30–2:10] The Report

**Narrate while Slack notification appears (or terminal output if no Slack):**
> "30 seconds later."

**Show the incident report:**
```
🔥 BurnRateBudgetAlert — CRITICAL
Summary: researcher-v1 is stuck in a retry loop causing 8-10x cost spike on burnrate-demo-app
Culprit: researcher-v1 → gen_ai chat
Root cause: SigNoz traces show researcher-v1 making 8-12 LLM calls per research task
            instead of 1. Input tokens grew from ~170 to ~1,400 per task due to retry context.
            Burn rate jumped from $0.0003/min to $0.0028/min — a 9.3x spike.
Cost impact: $10.98/hr · $263.52/day projected
Confidence: high
Evidence:
  • burnrate.cost.usd rate: 0.000047/s → 0.000183/s (3.9x above threshold)
  • researcher-v1 span count: 47 spans in 15min vs 5 baseline (9.4x normal)
  • gen_ai.usage.input_tokens p95: 1,387 tokens vs 171 baseline
Actions taken by Cost Guard:
  ✓ Throttled researcher-v1 to 2 calls/min — burn rate will drop within 60s
```

> "$263 a day. From one bug. Found in 30 seconds. No dashboards, no manual trace hunting."

---

### [2:10–2:35] The Evidence

**Show in SigNoz:**
1. "Burnrate Live" dashboard — burn rate spike clearly visible
2. "Cost by Agent" — researcher-v1 dwarfs summarizer-v1
3. Click into a trace — show a span with `gen_ai.usage.cost.total = 0.0847` and `gen_ai.usage.input_tokens = 78432`

**Narrate:**
> "And here it is in the trace. Every LLM call has `gen_ai.usage.cost.total`. You can filter traces by cost. Sort by cost. Alert on cost per operation. This is what the OTel spec should have had from the start."

---

### [2:35–3:00] Close

**Show GitHub repo README:**

> "Burnrate is open source, Apache-2. Install the SDK: `pip install burnrate-otel`. Point it at SigNoz. Done. We've also filed a formal proposal to add `gen_ai.usage.cost.*` to the upstream OpenTelemetry GenAI semantic conventions — the spec gap that made this necessary."

**Final line:**
> "Burnrate. Because token counts don't pay the bill. Dollars do."

---

## Backup Demo (if live chaos fails)

Pre-recorded GIF of the burn rate spike → Cost Guard → Slack report. Embed in README and show in browser tab if live system has issues.

## Troubleshooting

- **Cost Guard not receiving alerts**: SigNoz runs in Docker — webhook URL must be `http://host.docker.internal:8082/alert`, not `localhost`
- **Dashboard showing 0**: Demo app must be running and generating live requests (Rate aggregate needs ongoing data points)
- **Mock mode**: `COST_GUARD_MOCK=true` returns synthetic diagnosis without Anthropic credits — still demonstrates the full loop
