"""ResearchAgent — uses an LLM to research a topic. Chaos-injectable."""

from __future__ import annotations

import asyncio
import logging
import os

from anthropic import Anthropic
from opentelemetry import trace

from ..chaos import ChaosController

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_AGENT_ID = "researcher-v1"
_DEFAULT_MODEL = os.getenv("RESEARCHER_MODEL", "claude-haiku-4-5-20251001")
_EXPENSIVE_MODEL = "claude-sonnet-4-6"  # used when model_misroute chaos is active


class ResearchAgent:
    def __init__(self, chaos: ChaosController | None = None) -> None:
        self._client = Anthropic()
        self._chaos = chaos or ChaosController()
        self._context_history: list[dict] = []  # grows under prompt_bloat

    async def run(self, topic: str) -> str:
        # Cost Guard throttle check — if Cost Guard throttled this agent, slow it down.
        # This is what makes the self-healing loop visible in the demo.
        if self._chaos.is_throttled(_AGENT_ID):
            log.warning("researcher-v1 THROTTLED by Cost Guard — waiting 20s before proceeding")
            await asyncio.sleep(20)
        self._chaos.record_call(_AGENT_ID)

        model = self._resolve_model()
        max_retries = self._chaos.retry_count()

        with tracer.start_as_current_span(
            "gen_ai invoke_agent",
            attributes={
                "gen_ai.system": "anthropic",
                "gen_ai.operation.name": "invoke_agent",
                "gen_ai.request.model": model,
                "gen_ai.agent.name": "researcher",
                "burnrate.agent.id": _AGENT_ID,
                "burnrate.feature": "research-pipeline",
                "demo.chaos_scenario": self._chaos.active_scenario or "none",
                "demo.max_attempts": max_retries,
            },
        ) as span:
            result = ""
            for attempt in range(max_retries):
                with tracer.start_as_current_span(
                    "gen_ai chat",
                    attributes={
                        "gen_ai.system": "anthropic",
                        "gen_ai.operation.name": "chat",
                        "gen_ai.request.model": model,
                        "burnrate.agent.id": _AGENT_ID,
                        "burnrate.task.id": f"research:{topic[:30]}",
                        "demo.attempt": attempt + 1,
                        "demo.max_attempts": max_retries,
                    },
                ) as llm_span:
                    # Under retry_loop chaos: all attempts except the last are simulated
                    # RateLimit failures — exactly how a broken retry handler behaves.
                    # This makes traces show the pattern: N-1 failed spans + 1 success span,
                    # which Cost Guard's MCP investigation can identify as a retry loop.
                    if self._chaos.active_scenario == "retry_loop" and attempt < max_retries - 1:
                        llm_span.set_attribute("error.type", "RateLimitError")
                        llm_span.set_attribute("gen_ai.error.type", "rate_limit")
                        llm_span.set_attribute("demo.simulated_failure", True)
                        llm_span.set_attribute("gen_ai.usage.input_tokens", 0)
                        llm_span.set_attribute("gen_ai.usage.output_tokens", 0)
                        log.warning(
                            "retry_loop: simulated RateLimit on attempt %d/%d for topic=%r",
                            attempt + 1, max_retries, topic,
                        )
                        await asyncio.sleep(0.05)
                        continue

                    messages = self._build_messages(topic)
                    resp = self._client.messages.create(
                        model=model,
                        max_tokens=512,
                        messages=messages,
                        system="You are a concise research assistant. Summarize key facts about the given topic in 3 bullet points.",
                    )

                    usage = resp.usage
                    llm_span.set_attribute("gen_ai.response.model", resp.model)
                    llm_span.set_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
                    llm_span.set_attribute("gen_ai.usage.output_tokens", usage.output_tokens)
                    if hasattr(usage, "cache_creation_input_tokens"):
                        llm_span.set_attribute(
                            "gen_ai.usage.cache_creation_input_tokens",
                            usage.cache_creation_input_tokens or 0,
                        )
                    if hasattr(usage, "cache_read_input_tokens"):
                        llm_span.set_attribute(
                            "gen_ai.usage.cache_read_input_tokens",
                            usage.cache_read_input_tokens or 0,
                        )

                    result = resp.content[0].text

                    # Under prompt_bloat, accumulate context so each subsequent call
                    # is more expensive — input tokens grow with every invocation.
                    if self._chaos.active_scenario == "prompt_bloat":
                        self._context_history.append({"role": "user", "content": topic})
                        self._context_history.append({"role": "assistant", "content": result})
                        log.warning(
                            "prompt_bloat: context now %d messages (%d chars)",
                            len(self._context_history),
                            sum(len(m["content"]) for m in self._context_history),
                        )
                    break  # success — exit retry loop

            span.set_attribute("demo.successful_attempt", attempt + 1)
            return result

    def _resolve_model(self) -> str:
        if self._chaos.active_scenario == "model_misroute":
            log.warning("model_misroute: routing cheap task to %s", _EXPENSIVE_MODEL)
            return _EXPENSIVE_MODEL
        return _DEFAULT_MODEL

    def _build_messages(self, topic: str) -> list[dict]:
        base = [{"role": "user", "content": f"Research topic: {topic}"}]
        if self._chaos.active_scenario == "prompt_bloat" and self._context_history:
            return self._context_history + base
        return base
