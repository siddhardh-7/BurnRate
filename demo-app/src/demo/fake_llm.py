"""
Fake LLM backend — enabled with DEMO_FAKE_LLM=true.

Synthesizes responses and plausible token usage so the full cost pipeline
(BurnrateSpanProcessor → metrics → SigNoz → alert → Cost Guard) runs without
Anthropic credits. The fabrication stops at the API boundary: spans, cost
attributes, metrics, and the self-healing loop are all real telemetry.

Token accounting mirrors how the real API behaves in each chaos scenario:
input tokens scale with the actual prompt payload (so prompt_bloat grows
naturally), and cache reads vanish under cache_miss_storm.
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass


def enabled() -> bool:
    return os.getenv("DEMO_FAKE_LLM", "").strip().lower() in ("1", "true", "yes")


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class _TextBlock:
    text: str


@dataclass
class FakeResponse:
    model: str
    usage: _Usage
    content: list


def complete(
    model: str,
    messages: list[dict],
    system: str = "",
    max_tokens: int = 512,
    cache_hit: bool = True,
) -> FakeResponse:
    """Drop-in stand-in for anthropic.Anthropic().messages.create(...)."""
    payload_chars = len(system) + sum(len(m["content"]) for m in messages)
    # ~4 chars/token plus the fixed request overhead the real API bills for.
    input_tokens = 110 + payload_chars // 4 + random.randint(-6, 6)
    output_tokens = random.randint(int(max_tokens * 0.35), int(max_tokens * 0.7))
    cache_read = (
        int(input_tokens * random.uniform(0.5, 0.75))
        if cache_hit and input_tokens > 140
        else 0
    )
    time.sleep(random.uniform(0.25, 0.6))  # realistic span duration

    prompt_tail = messages[-1]["content"][-80:].replace("\n", " ")
    text = (
        f"[fake-llm] Synthesized {model} response ({output_tokens} tokens) "
        f"for prompt ending: …{prompt_tail}"
    )
    return FakeResponse(
        model=model,
        usage=_Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read,
        ),
        content=[_TextBlock(text)],
    )
