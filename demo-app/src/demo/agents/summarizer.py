"""SummarizerAgent — takes research output and produces a final summary."""

from __future__ import annotations

import os

from anthropic import Anthropic
from opentelemetry import trace

from .. import fake_llm
from ..chaos import ChaosController

tracer = trace.get_tracer(__name__)
_MODEL = os.getenv("SUMMARIZER_MODEL", "claude-haiku-4-5-20251001")


class SummarizerAgent:
    def __init__(self, chaos: ChaosController | None = None) -> None:
        self._client = None if fake_llm.enabled() else Anthropic()
        self._chaos = chaos or ChaosController()

    async def run(self, research_text: str) -> str:
        # Under cache_miss_storm, add a unique suffix to defeat prompt caching
        prompt_text = research_text
        if self._chaos.active_scenario == "cache_miss_storm":
            import random, string
            salt = "".join(random.choices(string.ascii_lowercase, k=12))
            prompt_text = f"{research_text}\n\n[ref:{salt}]"

        with tracer.start_as_current_span(
            "gen_ai chat",
            attributes={
                "gen_ai.system": "anthropic",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": _MODEL,
                "burnrate.agent.id": "summarizer-v1",
                "burnrate.feature": "research-pipeline",
            },
        ) as span:
            messages = [{"role": "user", "content": f"Summarize in one sentence:\n\n{prompt_text}"}]
            if fake_llm.enabled():
                resp = fake_llm.complete(
                    model=_MODEL,
                    messages=messages,
                    max_tokens=256,
                    cache_hit=self._chaos.active_scenario != "cache_miss_storm",
                )
            else:
                resp = self._client.messages.create(
                    model=_MODEL,
                    max_tokens=256,
                    messages=messages,
                )
            usage = resp.usage
            span.set_attribute("gen_ai.response.model", resp.model)
            span.set_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
            span.set_attribute("gen_ai.usage.output_tokens", usage.output_tokens)
            if hasattr(usage, "cache_read_input_tokens"):
                span.set_attribute("gen_ai.usage.cache_read_input_tokens", usage.cache_read_input_tokens or 0)
            if self._chaos.active_scenario == "cache_miss_storm":
                span.set_attribute("demo.cache_miss_forced", True)
            return resp.content[0].text
