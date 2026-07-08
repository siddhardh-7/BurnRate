# 3-Minute Demo Script

## Setup (before recording)
- Demo app running, generating baseline traffic: `docker-compose up`
- SigNoz "Burn Rate Live" dashboard open on screen, burn rate showing ~$0.14/hr (normal)
- Terminal 2: Cost Guard logs tailing: `docker compose logs -f cost-guard`
- Terminal 3: ready for chaos injection commands
- Slack open on side showing no alerts

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

**Run in terminal:**
```bash
curl -X POST http://localhost:8000/chaos/activate/retry_loop
# Then fire 10 concurrent requests:
for i in $(seq 1 10); do curl -s -X POST "http://localhost:8000/research?topic=AI+observability" & done; wait
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
INFO  Alert received: Burnrate: Budget Burn Rate Critical  state=firing
INFO  Investigating alert='Burnrate: Budget Burn Rate Critical' service='burnrate-demo-app'
INFO  [SigNoz MCP] signoz_query_metrics → burnrate.cost.usd by agent: researcher-v1=5.8/hr
INFO  [SigNoz MCP] signoz_search_traces → 847 spans from researcher-v1 in last 10min
INFO  [SigNoz MCP] signoz_search_logs → 42 retry warnings from researcher-v1
INFO  Diagnosis complete. Cost impact: $5.80/hr
```

---

### [1:30–2:10] The Report

**Narrate while Slack notification appears:**
> "30 seconds later. Slack."

**Show the Slack message (full text):**
```
🔥 Burnrate: Budget Burn Rate Critical — CRITICAL
Summary: researcher-agent stuck in a 42-iteration retry loop consuming ~78k tokens per task
Culprit: researcher-v1 → invoke_agent
Root cause: Error handling bug causes unbounded retries. Each retry re-sends full context.
            claude-sonnet-4-6 used due to model_misroute (expected haiku).
Cost impact: $5.80/hr · $139.20/day projected
Confidence: high
Evidence:
  • burnrate.cost.usd{agent=researcher-v1}: $0.14 → $5.80/hr at 14:32 (41× spike)
  • 847 spans from researcher-v1 in 10 min (baseline: ~20)
  • Trace abc123: 42 child LLM spans, all context growing, all retrying
Actions:
  1. Kill the retry loop — set MAX_RETRIES=3 in ResearchAgent
  2. Route topic-research tasks back to haiku (save 20× on model cost)
  3. Add circuit breaker to prevent unbounded retries
```

> "$139 a day. From one bug. Found in 30 seconds. No dashboards, no manual trace hunting."

---

### [2:10–2:35] The Evidence

**Show in SigNoz:**
1. "Burnrate Live" dashboard — burn rate spike clearly visible at 14:32
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
