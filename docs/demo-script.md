# Burnrate — Demo Film: "3:04 AM"

Not a product walkthrough — a three-minute story with the real system as its
spine. The viewer *feels* the incident before they understand the product; by
the time the report scrolls, they're not evaluating a tool, they're watching a
night they've lived get fixed. Every number and log line on screen matches what
the system actually produces in mock mode.

**Pipeline:** render story graphics (Remotion, `video/`) → generate voiceover
(ElevenLabs) → record real-system clips (QuickTime) → optional AI stills
(prompts below) → assemble (iMovie).

---

## The Narrative Design (why each beat exists)

| Beat | Device | Effect on the viewer |
|------|--------|----------------------|
| Cold open: a counter burning in the dark | **Loss aversion** — money visibly leaving, before any explanation | Visceral stake in the first 10 seconds |
| "It isn't your fault. It's the spec." | **Absolution** | Removes defensiveness; viewer joins your side |
| "One line" | **Effort collapse** — huge problem, tiny fix | The relief beat; makes the solution memorable |
| Re-creating the incident live | **Reenactment** | Turns a demo into a plot: we return to the scene of the crime, armed |
| "No human touched anything" | **Autonomy reveal** | The wow beat — the machine handles the 3 AM that opened the film |
| $263.52/day, 9.3×, 1,387 tokens | **Specificity** | Precise numbers read as truth; round numbers read as marketing |
| "The next 3:04 AM…" callback | **Narrative closure** | The open loop from second one gets closed in the final line |

---

## Timeline

| # | Clip | Source | Duration | Ends at |
|---|------|--------|---------:|--------:|
| 0 | Cold open — the burn counter | Remotion `coldopen.mp4` (+ optional AI stills intercut) | 14s | 0:14 |
| 1 | Title card | Remotion `intro.mp4` | 5s | 0:19 |
| 2 | Card 01 — THE BLIND SPOT | Remotion `card01.mp4` | 1.2s | 0:20 |
| 3 | Act 1: the spec gap | Screen + VO | 16s | 0:36 |
| 4 | Card 02 — ONE LINE | Remotion `card02.mp4` | 1.2s | 0:37 |
| 5 | Act 2: the fix | Screen + VO | 18s | 0:55 |
| 6 | Card 03 — THE INCIDENT | Remotion `card03.mp4` | 1.2s | 0:56 |
| 7 | Act 3: reenactment | Screen + VO | 22s | 1:18 |
| 8 | Card 04 — THE MACHINE WAKES | Remotion `card04.mp4` | 1.2s | 1:19 |
| 9 | Act 4a: Cost Guard log | Screen + VO | 24s | 1:43 |
| 10 | Act 4b: the incident report | Screen + VO | 26s | 2:09 |
| 11 | Card 05 — THE MORNING AFTER | Remotion `card05.mp4` | 1.2s | 2:10 |
| 12 | Act 5: the evidence | Screen + VO | 22s | 2:32 |
| 13 | Close: open source + upstream | Screen + VO | 16s | 2:48 |
| 14 | Outro card | Remotion `outro.mp4` | 7s | 2:55 |

Running long? Trim Act 5 to 16s, then drop cards 03–05.

---

## Music & Sound Design

Story needs a score arc, not one flat bed. All from Pixabay Music (free, no
attribution) — search terms given:

- **0:00–0:19** — low tension pulse ("dark ambient pulse"). Starts almost
  inaudible, swells with the counter.
- **0:19–0:56** — cut to near-silence under Act 1 (the gap lands harder in
  quiet), then a minimal warm bed enters with "One line" ("minimal technology
  ambient").
- **0:56–1:43** — tension returns for the incident ("suspense electronic
  minimal"), releases the moment `ACTION: throttled` appears.
- **1:43–2:55** — resolve to the warm bed again, slight lift for the outro.
- Keep music at ~10–12%, and apply iMovie's "Lower volume of other clips"
  (ducking) on every VO segment.

---

## Recording Hygiene

- Hide desktop icons (`defaults write com.apple.finder CreateDesktop false; killall Finder` — revert with `true` after), hide the Dock (⌥⌘D), hide bookmarks bar (⇧⌘B), close unrelated tabs.
- Do Not Disturb **on**. Browser zoom **110%** for SigNoz. Terminal: dark theme, ≥16pt, ~120×30, `⌘K` before every take.
- Cursor moves deliberately; point at what the VO names; never circle-scrub.
- QuickTime → New Screen Recording → full screen. Record each clip as its own
  file: `act1-spec.mov`, `act2-oneline.mov`, `act3-chaos.mov`, `act4a-log.mov`,
  `act4b-report.mov`, `act5-evidence.mov`, `close.mov`.

## Pre-Flight Checklist

Local dev mode assumed (SigNoz via `foundryctl cast`; demo-app and Cost Guard
via `uv run`). Docker Compose mode: use `docker logs -f burnrate-cost-guard`
for the tail and `http://burnrate-cost-guard:8082/alert` as the webhook.

- [ ] SigNoz UI up on `http://localhost:8080` (`foundryctl cast` if not)
- [ ] Demo app: `cd demo-app && uv run python -m demo.app`
- [ ] Cost Guard: `cd cost-guard && uv run python -m guard.webhook 2>&1 | tee /tmp/cost-guard.log`
- [ ] Webhook test → 200 in the Cost Guard log (channel: `http://host.docker.internal:8082/alert`)
- [ ] `curl -X POST http://localhost:8001/control/restore` and `curl -X POST http://localhost:8001/chaos/deactivate`
- [ ] Baseline traffic for 10+ min before recording:
  ```bash
  while true; do curl -s -X POST "http://localhost:8001/research/batch?count=2" > /dev/null; sleep 45; done
  ```
- [ ] Tabs in order: OTel GenAI spec (`gen_ai.usage.*` table) · Live Cost Monitor · Cost by Agent & Task · Traces (`service.name = burnrate-demo-app`) · Logs (both services) · GitHub README · the website
- [ ] Terminal 1: `tail -f /tmp/cost-guard.log` · Terminal 2: ready for chaos commands
- [ ] One full dry run end-to-end before the real takes

---

## The Film

VO blocks are TTS-ready — paste each into ElevenLabs as-is (drop the `>` marks).
One MP3 per block: `vo-cold.mp3`, `vo-act1.mp3` … `vo-close.mp3`.

### 0 — Cold Open (14s · Remotion `coldopen.mp4` · VO ≈ 33 words)

**SCREEN:** The rendered cold open: a dark frame, `03:04 AM` in the corner, a
dollar counter creeping from $0.47 and accelerating toward $847, an orange burn
line climbing across the dark. Hard cut to black on the final beat.

**Optional AI stills** (see prompts below): intercut two 2-second Ken Burns
cutaways — the sleeping engineer at ~0:04, the glowing phone at ~0:09. The
counter stays the anchor; the stills are texture.

**VO** *(slow, quiet, close to the mic — this is a bedtime story going wrong)*:
> Three-oh-four in the morning. Nobody is watching. An AI agent hits an error…
> and retries. And retries. Your observability stack sees every token it burns.
> It just can't see the money.

### 1 — Title Card (5s · `intro.mp4` · no VO)

Music swells one notch. The burn line from the cold open becomes the logo's
line — same shape, now under control.

### Act 1 — The Blind Spot (16s · VO ≈ 39 words)

**SCREEN:** OTel GenAI spec page. One slow scroll bringing the `gen_ai.usage.*`
token table center-frame; hold the last 4 seconds.

**VO:**
> This blind spot isn't your team's fault. It's written into the specification.
> The OpenTelemetry GenAI conventions define every token counter you could ask
> for. Input. Output. Cache. Reasoning. The word "cost" appears nowhere.

### Act 2 — One Line (18s · VO ≈ 44 words)

**SCREEN:** (a) ~7s: README quickstart at 150% zoom —
`provider.add_span_processor(BurnrateSpanProcessor())` fills the frame.
(b) ~11s: Live Cost Monitor, two calm baseline lines.

**VO:**
> The fix starts embarrassingly small. One line, added to the pipeline. Now
> every span carries its exact cost in dollars, and every agent's spend streams
> into SigNoz in real time. Two agents. Steady traffic. Fractions of a cent per
> minute.

### Act 3 — The Incident, Recreated (22s · VO ≈ 52 words)

**SCREEN:** (a) ~8s: Terminal 2, typed live:
```bash
curl -X POST http://localhost:8001/chaos/activate/retry_loop
curl -s -X POST "http://localhost:8001/research/batch?count=5"
```
(b) ~14s: Live Cost Monitor — researcher-v1 goes vertical, summarizer-v1 flat.
Hold the spike.

**VO:**
> So let's go back to that night — this time with Burnrate watching. We plant
> the same bug: a broken error handler, every call retrying eight to twelve
> times. There it is. Nine times baseline and climbing. And the chart already
> knows exactly who is spending the money.

### Act 4a — The Machine Wakes (24s · VO ≈ 57 words)

**SCREEN:** Terminal 1, the Cost Guard log tail. The alert fires on its own
(up to ~90s after the spike — record this clip after it lands):

```
INFO  Alert received: BurnRateBudgetAlert status=firing
INFO  Investigating alert='BurnRateBudgetAlert' service='burnrate-demo-app' severity='critical'
INFO  Diagnosis: culprit=researcher-v1 confidence=high cost=10.98/hr
INFO  HTTP Request: POST http://localhost:8001/control/throttle?agent_id=researcher-v1&max_calls_per_minute=2 "HTTP/1.1 200 OK"
INFO  ACTION: throttled agent=researcher-v1 to 2 calls/min
```

**VO:**
> This time, no one gets paged. The budget alert fires, and Cost Guard wakes
> instead. It investigates through SigNoz's own MCP server — querying cost
> metrics for the top spender, pulling traces to confirm the retry pattern.
> Diagnosis: researcher, high confidence. Then it acts. Throttled to two calls
> a minute. No human touched anything.

*(Real-LLM mode adds `[SigNoz MCP] calling tool:` lines here — keep them in
frame if you have credits; see Real-Mode Insert.)*

### Act 4b — The Report (26s · VO ≈ 61 words)

**SCREEN:** The incident report, scrolled slowly — the money shot. End on a
~4s cut back to Live Cost Monitor: the spike falling.

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

**VO:**
> Thirty seconds after the alert: a full incident report. Root cause. Evidence
> pulled from SigNoz. And the number that matters — two hundred sixty-three
> dollars a day, projected, from one bug. At demo scale. Swap in a production
> workload, and this is a four-thousand-dollar morning that never happens. And
> there — the throttle lands. The burn is already dying.

### Act 5 — The Morning After (22s · VO ≈ 51 words)

**SCREEN:** Three shots, ~7s each: (1) Cost by Agent & Task — the spend table,
researcher-v1 dwarfing summarizer-v1. (2) One `gen_ai chat` span open —
`gen_ai.usage.cost.total` beside the token counts. (3) Logs — both services in
one stream, demo-app's retry warnings above Cost Guard's `ACTION: throttled`.

**VO:**
> By morning, this isn't a war story — it's a queryable incident. Cost by
> agent, by task, by model. The dollar amount sits on the trace, next to the
> tokens it came from. And the whole night — retries, diagnosis, throttle —
> lives in SigNoz Logs. Traces, metrics, logs. One pipeline.

### Close (16s · VO ≈ 40 words)

**SCREEN:** (a) ~8s: the website hero, slow scroll to the deliverable cards.
(b) ~8s: GitHub README at the semconv proposal section.

**VO:**
> Burnrate is open source — one package, one line, pointed at SigNoz. And
> because the real fix belongs upstream, the repo ships a formal proposal to
> put cost into the OpenTelemetry spec itself. So the next three-oh-four AM…
> belongs to the machine.

### Outro (7s · `outro.mp4` · no VO)

"Token counts don't pay the bill. **Dollars do.**" Music resolves. Done.

---

## Graphics — Remotion (`video/`)

```bash
cd video
npm install        # first time only
npm run render     # renders all 8 pieces to video/out/
```

Outputs: `coldopen.mp4`, `intro.mp4`, `card01–05.mp4`, `outro.mp4` — 1080p/30fps.
(Remotion uses its own headless browser; it never touches your Chrome.)

## Optional AI Stills (cold-open texture)

Generate at 16:9 in Midjourney / DALL·E / Ideogram; use as 2s Ken Burns
cutaways inside the cold open. Skip these entirely if they look off — the
Remotion counter carries the open on its own.

**Still 1 — the sleeping engineer:**
> Cinematic photograph, a software engineer asleep at a home-office desk at
> night, face lit only by two dim monitors showing charts, dark room, moody
> teal and deep-orange color grade, shallow depth of field, shot on 35mm film,
> no text, no logos, 16:9.

**Still 2 — the phone that isn't ringing:**
> Cinematic close-up photograph, a smartphone face-up on a nightstand in a dark
> bedroom, screen off, faint orange light reflecting on it from a window, heavy
> shadows, quiet dread mood, teal-and-orange grade, shallow depth of field, no
> text, 16:9.

Rules: reject any output with garbled text or extra limbs; regenerate. Never
use AI imagery for product shots — every dashboard, log, and report in this
film is real.

## Voiceover — ElevenLabs

Use the **paste-ready tagged blocks in [`docs/vo-elevenlabs.md`](vo-elevenlabs.md)** —
they carry the delivery direction ([whispers], [pause], [emphasized], CAPS
stress) inline.

1. Free account (script total ≈ 2.8k chars, well within the 10k free tier).
2. Model **Eleven v3** (required — the audio tags only work there).
   Voice **Brian**. Stability **Natural**.
3. Generate all 8 blocks in one sitting → `vo-cold.mp3` … `vo-close.mp3`.
4. If "SigNoz" mispronounces, write "Sig-noze" and regenerate.

## Assembly — iMovie

1. Import everything; lay the timeline in the Timeline-table order.
2. VO under each clip, aligned to clip start; stretch/trim video to narration —
   never the audio.
3. Hard cuts everywhere except: a 0.5s cross-dissolve from the report into the
   recovery shot, and the cold open's final cut-to-black → title card (butt
   them directly; the rendered blackout is the transition).
4. Music per the sound-design arc above, ducked under all VO.
5. Export 1080p high quality. Watch the full export at volume before submitting.

## Backup Plan

Trigger the loop manually if the live alert misbehaves — output is identical:

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

Keep one recording of a full successful loop as splice-in insurance.

## Real-Mode Insert

With Anthropic credits: set `COST_GUARD_MOCK=false`, restart Cost Guard,
re-record **Act 4a only** — live `[SigNoz MCP] calling tool:` lines appear
between "Investigating" and "Diagnosis". Nothing else changes.

## Troubleshooting

- **Alert never reaches Cost Guard (local dev)** — webhook must be
  `http://host.docker.internal:8082/alert`, never `localhost`.
- **Alert never reaches Cost Guard (Docker Compose)** — use
  `http://burnrate-cost-guard:8082/alert`.
- **Dashboard flat at 0** — baseline-traffic loop stopped; restart it.
- **Port 8082 busy** — `pkill -f "guard.webhook"`, restart.
- **Mock vs real** — `COST_GUARD_MOCK=true` needs no credits; loop, throttle,
  and report are all real either way.
