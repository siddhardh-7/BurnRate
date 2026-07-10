# "3:04 AM" — Voiceover Blocks (ElevenLabs Eleven v3)

Paste each block into ElevenLabs **exactly as written**, one generation per block.

**Setup (once):** Model **Eleven v3** · Voice **Brian** · Stability **Natural** ·
download each result as the filename shown.

> ⚠️ These blocks use v3 **audio tags** (`[pause]`, `[whispers]`, …). They only
> work on Eleven v3. On Multilingual v2 the tags get read aloud — don't mix.

Tips: generate all blocks in one sitting for tonal consistency. If a take comes
out overacted, regenerate — v3 varies more per take than v2. If "SigNoz"
mispronounces, replace it with "Sig-noze".

---

## vo-cold.mp3 — Cold Open (target ≈ 13s)

```
[whispers] Three-oh-four in the morning. [long pause] Nobody is watching. [pause] [speaking softly] An AI agent hits an error... and retries. [short pause] And retries. [pause] Your observability stack sees every token it burns. [long pause] [emphasized] It just can't see the MONEY.
```

## vo-act1.mp3 — The Blind Spot (target ≈ 15s)

```
This blind spot isn't your team's fault. [short pause] It's written into the specification. [pause] The OpenTelemetry GenAI conventions define every token counter you could ask for. Input. Output. Cache. Reasoning. [long pause] The word "cost" appears... [pause] NOWHERE.
```

## vo-act2.mp3 — One Line (target ≈ 17s)

```
The fix starts embarrassingly small. [pause] ONE line, added to the pipeline. [short pause] Now every span carries its exact cost in dollars — and every agent's spend streams into SigNoz in real time. [pause] Two agents. Steady traffic. Fractions of a cent per minute.
```

## vo-act3.mp3 — The Incident (target ≈ 21s)

```
So let's go back to that night — [short pause] this time, with Burnrate watching. [pause] We plant the same bug: a broken error handler, every call retrying eight to twelve times. [long pause] [dramatic tone] There it is. [pause] NINE times baseline... and climbing. [short pause] And the chart already knows exactly WHO is spending the money.
```

## vo-act4a.mp3 — The Machine Wakes (target ≈ 23s)

```
This time, no one gets paged. [pause] The budget alert fires — and Cost Guard wakes instead. [short pause] It investigates through SigNoz's own MCP server. Querying cost metrics for the top spender. Pulling traces to confirm the retry pattern. [pause] Diagnosis: researcher. High confidence. [long pause] Then it acts. [short pause] Throttled, to two calls a minute. [pause] [emphasized] No human touched anything.
```

## vo-act4b.mp3 — The Report (target ≈ 25s)

```
Thirty seconds after the alert: a full incident report. [short pause] Root cause. Evidence pulled from SigNoz. And the number that matters — [pause] two hundred sixty-three dollars a day, projected, from ONE bug. [short pause] At demo scale. [pause] Swap in a production workload... and this is a four-thousand-dollar morning that never happens. [long pause] And there — the throttle lands. [short pause] The burn is already dying.
```

## vo-act5.mp3 — The Morning After (target ≈ 21s)

```
By morning, this isn't a war story. [short pause] It's a queryable incident. [pause] Cost by agent. By task. By model. The dollar amount sits on the trace, right next to the tokens it came from. [short pause] And the whole night — retries, diagnosis, throttle — lives in SigNoz Logs. [pause] Traces. Metrics. Logs. [emphasized] ONE pipeline.
```

## vo-close.mp3 — Close (target ≈ 15s)

```
Burnrate is open source. One package. One line. Pointed at SigNoz. [pause] And because the real fix belongs upstream, the repo ships a formal proposal to put COST into the OpenTelemetry spec itself. [long pause] [whispers] So the next three-oh-four AM... [pause] belongs to the machine.
```

---

## Fallback — if you must use Multilingual v2

Strip every `[tag]`, keep the CAPS, and replace pauses with break tags:
`[pause]` → `<break time="0.7s" />` · `[short pause]` → `<break time="0.4s" />` ·
`[long pause]` → `<break time="1.2s" />`. The whispered cold open won't whisper
on v2 — it relies on v3.
