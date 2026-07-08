"""
OTel metric emission for cost observability.
Counters for cumulative spend and tokens; histogram for per-operation cost distribution.
"""

from __future__ import annotations

from typing import Any

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, Meter

from .semconv import (
    METRIC_COST_PER_OP,
    METRIC_COST_TOTAL,
    METRIC_TOKENS_CACHE_CREATION,
    METRIC_TOKENS_CACHE_READ,
    METRIC_TOKENS_INPUT,
    METRIC_TOKENS_OUTPUT,
)


class CostMetrics:
    def __init__(self, meter: Meter | None = None) -> None:
        m = meter or metrics.get_meter("burnrate.otel", "0.1.0")

        self._cost_counter: Counter = m.create_counter(
            name=METRIC_COST_TOTAL,
            unit="USD",
            description="Cumulative LLM cost in USD attributed to each agent/task/user/model.",
        )
        self._cost_histogram: Histogram = m.create_histogram(
            name=METRIC_COST_PER_OP,
            unit="USD",
            description="Distribution of per-operation LLM cost in USD.",
        )
        self._input_tokens: Counter = m.create_counter(
            name=METRIC_TOKENS_INPUT,
            unit="tokens",
            description="Cumulative input tokens consumed.",
        )
        self._output_tokens: Counter = m.create_counter(
            name=METRIC_TOKENS_OUTPUT,
            unit="tokens",
            description="Cumulative output tokens generated.",
        )
        self._cache_read_tokens: Counter = m.create_counter(
            name=METRIC_TOKENS_CACHE_READ,
            unit="tokens",
            description="Cumulative cache-read input tokens (Anthropic prompt cache hits).",
        )
        self._cache_creation_tokens: Counter = m.create_counter(
            name=METRIC_TOKENS_CACHE_CREATION,
            unit="tokens",
            description="Cumulative cache-creation input tokens (Anthropic prompt cache writes).",
        )

    def record(
        self,
        cost: dict[str, float],
        attrs: dict[str, Any],
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> None:
        total = cost["total"]
        if total > 0:
            self._cost_counter.add(total, attrs)
            self._cost_histogram.record(total, attrs)
        if input_tokens:
            self._input_tokens.add(input_tokens, attrs)
        if output_tokens:
            self._output_tokens.add(output_tokens, attrs)
        if cache_read_tokens:
            self._cache_read_tokens.add(cache_read_tokens, attrs)
        if cache_creation_tokens:
            self._cache_creation_tokens.add(cache_creation_tokens, attrs)
