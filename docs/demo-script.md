# Burnrate — Demo Video Production Script

A complete production plan for the 3-minute submission video: shot list, TTS-ready
voiceover, animated graphics, and assembly guide. Every number and log line shown
on screen matches what the system actually produces in mock mode — no aspirational
output.

**Pipeline:** record clips (QuickTime) → generate voiceover (ElevenLabs) → render
brand cards (Remotion, in `video/`) → assemble (iMovie).

---

## Timeline at a Glance

| # | Clip | Type | Duration | Ends at |
|---|------|------|---------:|--------:|
| 0 | Intro card | Remotion `Intro` | 5.0s | 0:05 |
| 1 | Chapter 01 card — THE GAP | Remotion `Card01` | 1.2s | 0:06 |
| 2 | The spec gap | Screen + VO | 18s | 0:24 |
| 3 | Chapter 02 card — ONE LINE | Remotion `Card02` | 1.2s | 0:26 |
| 4 | One-line integration | Screen + VO | 20s | 0:46 |
| 5 | Chapter 03 card — INJECT CHAOS | Remotion `Card03` | 1.2s | 0:47 |
| 6 | Chaos injection + spike | Screen + VO | 22s | 1:09 |
| 7 | Chapter 04 card — COST GUARD | Remotion `Card04` | 1.2s | 1:10 |
| 8 | Cost Guard activates | Screen + VO | 30s | 1:40 |
| 9 | The incident report | Screen + VO | 30s | 2:10 |
| 10 | Chapter 05 card — THE EVIDENCE | Remotion `Card05` | 1.2s | 2:12 |
| 11 | Evidence trail | Screen + VO | 24s | 2:36 |
| 12 | Close | Screen + VO | 16s | 2:52 |
| 13 | Outro card | Remotion `Outro` | 7.0s | 2:59 |

Running long? Cut in this order: chapter cards 03–05, then trim clip 11 to 18s.

---

## Recording Hygiene (do these before any capture)

- **Clean the frame**: hide desktop icons (`defaults write com.apple.finder CreateDesktop false; killall Finder` — revert with `true` after), hide the Dock (⌥⌘D), hide browser bookmarks bar (⇧⌘B), close every unrelated tab.
- **Do Not Disturb on** — one Slack ping ruins a take.
- **Browser zoom 110%** for SigNoz so panel text is legible at 1080p.
- **Terminal**: dark theme, font ≥16pt, window ~120×30. Clear scrollback before each take (`⌘K`).
- **Cursor**: move deliberately, point at what the VO mentions, never circle-scrub.
- QuickTime → File → New Screen Recording → record **full screen**. iMovie will downscale retina to 1080p on export.
- Record each clip as its **own file**, named `clip-02-gap.mov`, `clip-04-oneline.mov`, etc. Segment recording kills the alert-wait dead air and makes retakes cheap.

---

## Pre-Flight Checklist

This assumes **local dev mode** (SigNoz via `foundryctl cast`; demo-app and Cost
Guard via `uv run` on the host). For Docker Compose mode, substitute
`docker logs -f burnrate-cost-guard` for the log tail and
`http://burnrate-cost-guard:8082/alert` as the webhook URL.

- [ ] SigNoz running (UI on `http://localhost:8080`) — start with `foundryctl cast` if not already up
- [ ] Demo app running: `cd demo-app && uv run python -m demo.app` (port 8001)
- [ ] Cost Guard running: `cd cost-guard && uv run python -m guard.webhook 2>&1 | tee /tmp/cost-guard.log` (port 8082)
- [ ] Webhook test: notification channel is `http://host.docker.internal:8082/alert` — send a test notification, confirm 200 in the Cost Guard log
- [ ] No leftover throttles: `curl -X POST http://localhost:8001/control/restore`
- [ ] Chaos deactivated: `curl -X POST http://localhost:8001/chaos/deactivate`
- [ ] Baseline traffic running for 10+ min so dashboards show a calm "before":
  ```bash
  while true; do curl -s -X POST "http://localhost:8001/research/batch?count=2" > /dev/null; sleep 45; done
  ```
- [ ] Browser tabs open, in order:
  1. OTel GenAI spec — `opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/` scrolled to the `gen_ai.usage.*` table
  2. SigNoz → **Burnrate — Live Cost Monitor** (time range: last 30 min)
  3. SigNoz → **Burnrate — Cost by Agent & Task**
  4. SigNoz → Traces (filtered to `service.name = burnrate-demo-app`)
  5. SigNoz → Logs (filtered to `service.name IN (burnrate-demo-app, burnrate-cost-guard)`)
  6. GitHub repo README
  7. `https://siddhardh-7.github.io/BurnRate/` (the website)
- [ ] Terminal 1: `tail -f /tmp/cost-guard.log`
- [ ] Terminal 2: prompt ready for chaos commands
- [ ] Do one full dry run end-to-end before recording — it flushes stale metrics, confirms the alert threshold, and warms up the flow.

---

## Clips

Each clip has **SCREEN** (what you record) and **VO** (the exact text to paste
into ElevenLabs — one audio file per clip, named `vo-02.mp3` etc.). Word counts
are tuned to the clip duration at documentary narration pace; if an audio file
runs ±2s, stretch or trim the screen footage, never the audio.

### Clip 2 — The Spec Gap (18s · VO ≈ 44 words)

**SCREEN:** OTel GenAI spec page. Slow, single scroll that brings the
`gen_ai.usage.*` token attributes table into center frame. Hold on the table for
the last 5 seconds. No clicking.

**VO:**
> The OpenTelemetry GenAI spec tracks everything about your AI agents. Every input
> token. Every output token. Cache hits. Reasoning tokens. Everything — except a
> single dollar. So when an agent runs wild at 3 AM, your dashboards show tokens
> burned. Not money lost.

### Clip 4 — One Line (20s · VO ≈ 49 words)

**SCREEN:** Two shots, cut in iMovie. (a) ~7s: the README quickstart snippet —
zoom browser to 150% so this line fills the frame:
`provider.add_span_processor(BurnrateSpanProcessor())`. (b) ~13s: SigNoz
**Live Cost Monitor**, calm baseline lines for researcher-v1 and summarizer-v1.

**VO:**
> This is Burnrate. One line added to our agent pipeline, and SigNoz now sees real
> dollar costs. Every span carries its exact cost in dollars. Every agent's spend
> streams into live metrics, broken down by agent and by model. Two agents, steady
> traffic, fractions of a cent per minute. Normal.

### Clip 6 — Inject Chaos (22s · VO ≈ 54 words)

**SCREEN:** (a) ~8s: Terminal 2, type these live — don't paste:
```bash
curl -X POST http://localhost:8001/chaos/activate/retry_loop
curl -s -X POST "http://localhost:8001/research/batch?count=5"
```
(b) ~14s: cut to **Live Cost Monitor**. The researcher-v1 line spikes;
summarizer-v1 stays flat. Hold the spike.

**VO:**
> Let's plant tonight's three-A-M bug. The researcher agent now has a broken error
> handler — every call retries eight to twelve times, dragging its accumulated
> context back in each attempt. Watch the burn rate. There it is. Nine times
> baseline, and climbing. The summarizer, same service, stays flat. This chart
> shows you who is spending your money.

### Clip 8 — Cost Guard Activates (30s · VO ≈ 73 words)

**SCREEN:** Terminal 1, the Cost Guard log tail. The alert fires on its own
(rule evaluates every minute; expect up to ~90s after the spike — this is why you
record in segments). What actually appears:

```
INFO  Alert received: BurnRateBudgetAlert status=firing
INFO  Investigating alert='BurnRateBudgetAlert' service='burnrate-demo-app' severity='critical'
INFO  Diagnosis: culprit=researcher-v1 confidence=high cost=10.98/hr
INFO  HTTP Request: POST http://localhost:8001/control/throttle?agent_id=researcher-v1&max_calls_per_minute=2 "HTTP/1.1 200 OK"
INFO  ACTION: throttled agent=researcher-v1 to 2 calls/min
```

**VO:**
> No human touched anything. The SigNoz budget alert fired, and Cost Guard woke up.
> It investigates through SigNoz's own MCP server — the official one — querying
> cost metrics to find the top spender, pulling traces to confirm the retry
> pattern, checking token counts for the blast radius. Diagnosis: researcher
> version one, high confidence. Then it acts. The culprit is throttled to two
> calls a minute. Live. Automatically.

*(If recording in real-LLM mode, `[SigNoz MCP] calling tool:` lines appear here —
keep them in frame, they're the best part.)*

### Clip 9 — The Incident Report (30s · VO ≈ 71 words)

**SCREEN:** The report in the Cost Guard terminal (or Slack if configured).
Scroll it slowly, top to bottom — this is the money shot:

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

End the clip by cutting back to **Live Cost Monitor** for ~4s: the researcher-v1
line falling back toward baseline.

**VO:**
> Thirty seconds after the alert: a full incident report. Root cause. Evidence
> pulled from SigNoz. Dollar impact — two hundred sixty-three dollars a day,
> projected, from one bug. Found and stopped with no dashboards opened and no
> traces hunted by hand. And this is demo scale — swap in a production workload
> and that same bug is a four-thousand-dollar morning. And there's the throttle
> landing. Burn rate's already coming down.

### Clip 11 — The Evidence Trail (24s · VO ≈ 58 words)

**SCREEN:** Three shots, ~8s each:
1. **Cost by Agent & Task** — the "Top Agents by Total Spend" table, researcher-v1 dwarfing summarizer-v1
2. Traces → open one `gen_ai chat` span → attributes panel showing `gen_ai.usage.cost.total` / `.input` / `.output` beside the token counts
3. Logs → both services in one stream — demo-app's retry warnings and Cost Guard's `ACTION: throttled` line

**VO:**
> Everything stays queryable. Cost by agent, by task, by model. On the individual
> trace, the dollar cost sits right next to the token counts it was derived from —
> filter by it, sort by it, alert on it. And the whole incident narrative lives in
> SigNoz Logs, correlated with those same traces. Traces, metrics, and logs. One
> pipeline.

### Clip 12 — Close (16s · VO ≈ 40 words)

**SCREEN:** (a) ~8s: the website hero (`siddhardh-7.github.io/BurnRate`) — slow
scroll to the three deliverable cards. (b) ~8s: GitHub README at the semconv
proposal section.

**VO:**
> Burnrate is open source, Apache two. One pip-installable package — add one line,
> point OTLP at SigNoz, done. And because the real fix belongs upstream, the repo
> ships a formal proposal to add cost attributes to the OpenTelemetry spec itself.

*(The outro card carries the closing tagline visually — no VO over it, just music.)*

---

## Graphics — Remotion (`video/`)

The animated cards live in `video/` as a Remotion project (brand-matched: the
logo line-draw animation, chapter cards, outro). Render them yourself:

```bash
cd video
npm install
npm run render        # renders all 7 cards to video/out/*.mp4
```

> Remotion downloads its own headless browser on first render — it does not
> touch your Chrome.

Outputs: `intro.mp4`, `card01.mp4` … `card05.mp4`, `outro.mp4` — 1920×1080, 30fps,
drop straight into iMovie.

---

## Voiceover — ElevenLabs

1. Create a free account at elevenlabs.io (free tier ≈ 10k chars/month; this
   script uses ~2.5k).
2. Voice: **Brian** or **Adam** (calm, documentary). Model: Multilingual v2.
3. Settings: Stability **50%**, Similarity **75%**, Style **0%**, Speaker boost on.
4. Paste each clip's VO block (just the text, not the `>` marks) → generate →
   download as `vo-02.mp3`, `vo-04.mp3`, `vo-06.mp3`, `vo-08.mp3`, `vo-09.mp3`,
   `vo-11.mp3`, `vo-12.mp3`.
5. Listen once for mispronunciations. If "SigNoz" comes out wrong, spell it
   "Sig-noze" in the text and regenerate.

---

## Assembly — iMovie

1. New Movie → import all `clip-*.mov`, `vo-*.mp3`, and `video/out/*.mp4`.
2. Lay the timeline in the Timeline-at-a-Glance order: `intro.mp4`, `card01.mp4`,
   `clip-02-gap.mov`, `card02.mp4`, …, `outro.mp4`.
3. Drag each `vo-*.mp3` under its screen clip; align the audio start with the
   clip start; trim/extend the video to the narration.
4. Transitions: **none** between cards and clips (hard cuts read as confident).
   One exception: 0.5s cross-dissolve from clip 9's report into the dashboard
   recovery shot.
5. Music (optional but recommended): one low ambient tech track under the whole
   video (Pixabay Music → search "technology ambient" — free, no attribution).
   Volume ~12%, and use iMovie's "Lower volume of other clips" (ducking) on every
   VO segment.
6. Export: File → Share → File → 1080p, High quality, Faster compress off.
7. Watch the export start-to-finish once at full volume before submitting.

---

## Backup Plan (if live chaos misbehaves on camera)

The E2E loop can be triggered manually without waiting for SigNoz's evaluator —
the Cost Guard output is identical:

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

Keep one screen recording of a successful full loop as splice-in insurance.

## Optional Real-Mode Insert

If Anthropic credits are added before recording: set `COST_GUARD_MOCK=false` in
`.env`, restart Cost Guard, and re-record **clip 8 only** — the log then shows
live `[SigNoz MCP] calling tool: signoz_query_metrics` lines between "Investigating"
and "Diagnosis". Nothing else in the video changes.

## Troubleshooting

- **Alert never reaches Cost Guard (local dev)** — webhook URL must be
  `http://host.docker.internal:8082/alert`, never `localhost` (SigNoz is in Docker).
- **Alert never reaches Cost Guard (Docker Compose)** — use
  `http://burnrate-cost-guard:8082/alert` (both on `signoz-network`).
- **Dashboard lines flat at 0** — the baseline-traffic loop stopped; restart it.
- **Port 8082 in use** — stale Cost Guard: `pkill -f "guard.webhook"`, restart.
- **Mock vs real** — `COST_GUARD_MOCK=true` (default) needs no credits; the loop,
  throttle, and report are all real. `false` + `ANTHROPIC_API_KEY` shows live MCP
  tool calls.
