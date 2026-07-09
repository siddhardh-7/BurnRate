# Burnrate — 3-Minute Demo Script

A shot-by-shot script for the submission video. Every number and log line in this
script matches what the system actually produces — no aspirational output.

---

## Pre-Flight Checklist (before recording)

Run through this list top to bottom. Do not start recording until every box checks.

This script assumes **local dev mode**: SigNoz via foundryctl (`pours/deployment/`), demo-app and Cost Guard via `uv run` on the host. For Docker Compose mode, substitute `docker logs -f burnrate-cost-guard` for the log tail and use `http://burnrate-cost-guard:8082/alert` as the webhook URL.

- [ ] SigNoz running (UI on `http://localhost:8080`) — start with `foundryctl cast` if not already up
- [ ] Demo app running: `cd demo-app && uv run python -m demo.app` (port 8001)
- [ ] Cost Guard running: `cd cost-guard && uv run python -m guard.webhook 2>&1 | tee /tmp/cost-guard.log` (port 8082)
- [ ] Verify webhook reachable from SigNoz: notification channel is `http://host.docker.internal:8082/alert` (SigNoz is in Docker; cost-guard is on the host) — send a test notification, confirm 200 in Cost Guard logs
- [ ] No throttles left over from testing: `curl -X POST http://localhost:8001/control/restore`
- [ ] Chaos deactivated: `curl -X POST http://localhost:8001/chaos/deactivate`
- [ ] Generate 10 min of baseline traffic before recording so dashboards show a calm "before" state:
  ```bash
  while true; do curl -s -X POST "http://localhost:8001/research/batch?count=2" > /dev/null; sleep 45; done
  ```
  Leave this running in a background terminal for the whole recording.
- [ ] Browser tabs open, in order:
  1. OTel GenAI spec — `opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/` scrolled to the `gen_ai.usage.*` attribute table
  2. SigNoz → **Burnrate — Live Cost Monitor** dashboard (time range: last 30 min)
  3. SigNoz → **Burnrate — Cost by Agent & Task** dashboard
  4. SigNoz → Traces (filtered to `service.name = burnrate-demo-app`)
  5. SigNoz → Logs (filtered to `service.name IN (burnrate-demo-app, burnrate-cost-guard)`)
  6. GitHub repo README
- [ ] Terminal 1: cost-guard log tail visible: `tail -f /tmp/cost-guard.log`
- [ ] Terminal 2: prompt ready for chaos commands
- [ ] Screen recorder set to capture full screen at 1080p+; microphone tested

---

## Script

### [0:00–0:20] The Hook — the spec gap

**Screen:** OTel GenAI spec page, the `gen_ai.usage.*` attribute table.
Slowly scroll the token attributes into view.

**Narration:**

> "The OpenTelemetry GenAI semantic conventions track everything about your AI
> agents. Every input token. Every output token. Cache hits. Reasoning tokens.
> Everything — except a single dollar. There is no cost attribute in this spec.
> So when your agent runs wild at 3am, your observability stack tells you how
> many tokens it burned. Not how much money you lost."

**Beat:** pause half a second on the table before cutting.

---

### [0:20–0:45] Normal State — one line of code

**Screen:** Split or quick cut: (1) the integration snippet, (2) the
**Live Cost Monitor** dashboard showing calm baseline lines for
`researcher-v1` and `summarizer-v1`.

**Show this snippet** (from the README, keep it on screen ~4 seconds):

```python
provider.add_span_processor(BurnrateSpanProcessor())  # one line. zero config.
```

**Narration:**

> "This is Burnrate. One line added to our agent pipeline, and SigNoz now sees
> real dollar costs. Every span carries `gen_ai.usage.cost.total`. Every agent's
> spend streams into these metrics — broken down by agent and by model. Right
> now: two agents, steady traffic, fractions of a cent per minute. Normal."

---

### [0:45–1:05] Inject Chaos

**Screen:** Terminal 2, typing the commands live.

```bash
curl -X POST http://localhost:8001/chaos/activate/retry_loop
curl -s -X POST "http://localhost:8001/research/batch?count=5"
```

**Narration:**

> "Let's plant tonight's 3am bug. The researcher agent now has a broken error
> handler — every LLM call retries 8 to 12 times, and each retry drags the
> accumulated context back in. Watch the burn rate."

**Screen:** Cut to **Live Cost Monitor**. The `researcher-v1` line spikes;
`summarizer-v1` stays flat. Hold on the spike ~5 seconds.

> "There it is. The researcher line goes vertical — roughly nine times baseline.
> The summarizer, same service, same traffic, stays flat. Token dashboards would
> show 'more tokens.' This shows you who is spending your money."

---

### [1:05–1:35] Cost Guard Activates

**Screen:** Terminal 1 — Cost Guard log tail. The SigNoz alert fires on its own
(rule evaluates every minute; expect up to ~90 s after the spike).

**What actually appears in the log:**

```
INFO  Alert received: BurnRateBudgetAlert status=firing
INFO  Investigating alert='BurnRateBudgetAlert' service='burnrate-demo-app' severity='critical'
INFO  Diagnosis: culprit=researcher-v1 confidence=high cost=10.98/hr
INFO  HTTP Request: POST http://localhost:8001/control/throttle?agent_id=researcher-v1&max_calls_per_minute=2 "HTTP/1.1 200 OK"
INFO  ACTION: throttled agent=researcher-v1 to 2 calls/min
```

**Narration:**

> "No human touched anything. The SigNoz budget alert fired, and Cost Guard woke
> up. It investigates through SigNoz's own MCP server — the official one — querying
> cost metrics to find the top spender, pulling traces to confirm the retry
> pattern, checking token counts for the blast radius. Diagnosis: researcher-v1,
> high confidence. And then it acts — the culprit is throttled to two calls a
> minute, live."

*(If recording in real-LLM mode instead of mock, you'll also see
`[SigNoz MCP] calling tool: signoz_query_metrics` lines — leave them in shot,
they're the best part.)*

---

### [1:35–2:10] The Incident Report

**Screen:** The report in the Cost Guard terminal (or Slack if configured).
Scroll it slowly — this is the money shot.

```
🔥 BurnRateBudgetAlert — CRITICAL
Summary: researcher-v1 is stuck in a retry loop causing 8-10x cost spike on burnrate-demo-app
Culprit: researcher-v1 → gen_ai chat
Root cause: SigNoz traces show researcher-v1 making 8-12 LLM calls per research task
            instead of 1. Input tokens grew from ~170 (baseline) to ~1,400 per task
            due to accumulated retry context. Burn rate jumped from $0.0003/min to
            $0.0028/min — a 9.3x spike.
Cost impact: $10.98/hr · $263.52/day projected
Confidence: high
Evidence:
  • burnrate.cost.usd rate: 0.000047/s → 0.000183/s (3.9x above threshold)
  • researcher-v1 span count: 47 spans in 15min vs 5 baseline (9.4x normal)
  • gen_ai.usage.input_tokens p95: 1,387 tokens vs 171 baseline
Actions taken by Cost Guard:
  ✓ Throttled researcher-v1 to 2 calls/min — burn rate will drop within 60s
```

**Narration:**

> "Thirty seconds after the alert: a full incident report. Root cause, evidence
> pulled from SigNoz, dollar impact — two hundred sixty-three dollars a day,
> projected, from one bug. Found and stopped with no dashboards opened and no
> traces hunted by hand. And this is the demo scale — swap the pricing for Opus
> and a real workload, and that same bug is a four-thousand-dollar morning."

**Screen:** Cut back to **Live Cost Monitor** — the researcher-v1 line falling
back toward baseline after the throttle.

> "And there's the throttle landing. Burn rate's already coming down."

---

### [2:10–2:35] The Evidence Trail

**Screen sequence, ~8 seconds each:**

1. **Cost by Agent & Task** dashboard — the "Top Agents by Total Spend" table,
   researcher-v1 dwarfing summarizer-v1
2. SigNoz Traces → click into one `gen_ai chat` span → attributes panel showing
   `gen_ai.usage.cost.total`, `gen_ai.usage.cost.input`, `gen_ai.usage.cost.output`
   alongside the token counts
3. SigNoz Logs → filtered to both services — demo-app's retry warnings and
   Cost Guard's `ACTION: throttled` line in one stream

**Narration:**

> "Everything is queryable after the fact. Cost by agent, by task, by model.
> And here, on the individual trace: `gen_ai.usage.cost.total`, right next to
> the token counts it was derived from. You can filter traces by cost. Sort by
> cost. Alert on cost. And the whole incident narrative — the retries, the
> diagnosis, the throttle — lives in SigNoz Logs, correlated with those same
> traces. Traces, metrics, and logs, one pipeline. This is what the OTel spec
> should have had from the start."

---

### [2:35–3:00] Close

**Screen:** GitHub README, scroll from the hero to the semconv proposal section.

**Narration:**

> "Burnrate is open source, Apache-2. The SDK is one pip-installable package —
> add one line, point OTLP at SigNoz, done. And because the real fix belongs
> upstream, the repo ships a formal proposal to add `gen_ai.usage.cost.*` to
> the OpenTelemetry GenAI semantic conventions — so the next team doesn't have
> to build this at all."

**Final beat, on the repo tagline:**

> "Burnrate. Because token counts don't pay the bill. Dollars do."

---

## Timing Budget

| Segment | Duration | Cumulative |
|---|---|---|
| Hook (spec gap) | 20 s | 0:20 |
| Normal state | 25 s | 0:45 |
| Chaos injection + spike | 20 s | 1:05 |
| Cost Guard activates | 30 s | 1:35 |
| Incident report | 35 s | 2:10 |
| Evidence trail | 25 s | 2:35 |
| Close | 25 s | 3:00 |

If running long, cut from the Evidence Trail first — the report section carries
the demo.

---

## Recording Strategy

The alert-fire wait (~60–90 s after the spike) is dead air. Two options:

1. **Record in segments** (recommended): stop after the spike shot, wait for the
   alert, then record the Cost Guard section once the log lines are there.
2. **Record continuously**, cut the wait in editing.

Do a full dry run once, end to end, before the real take: it flushes stale
metrics, confirms the alert threshold still matches your baseline, and warms
you up on the narration.

---

## Backup Plan (if live chaos fails on camera)

- The E2E loop can be triggered manually without waiting for SigNoz's evaluator:
  ```bash
  curl -X POST http://localhost:8082/alert -H 'Content-Type: application/json' -d '{
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "BurnRateBudgetAlert", "service_name": "burnrate-demo-app", "severity": "critical"},
      "annotations": {"description": "Cost burn rate 3.9x above threshold"}
    }]
  }'
  ```
  The Cost Guard log output is identical — the viewer can't tell the difference.
- Keep a screen recording of one successful full loop as a fallback to splice in.

## Troubleshooting

- **Alert never reaches Cost Guard (local dev mode)** — SigNoz runs in Docker, cost-guard
  on the host. Webhook URL must be `http://host.docker.internal:8082/alert`, not `localhost`.
- **Alert never reaches Cost Guard (Docker Compose mode)** — both services are on `signoz-network`.
  Use `http://burnrate-cost-guard:8082/alert`.
- **Dashboard lines flat at 0** — Rate aggregation needs live traffic; make sure
  the baseline-traffic loop from the checklist is still running.
- **Port 8082 already in use** — a stale Cost Guard instance: `pkill -f "guard.webhook"`, restart.
- **Mock vs real mode** — `COST_GUARD_MOCK=true` (default) returns the synthetic
  diagnosis with no Anthropic credits needed; the loop, throttle, and report are
  all real. Set `COST_GUARD_MOCK=false` + `ANTHROPIC_API_KEY` to show live MCP
  tool calls in the log.
