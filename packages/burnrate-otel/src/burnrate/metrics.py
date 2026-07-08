"""
OTel metric emission for cost observability.
Creates a Counter (cumulative USD spend) and a Histogram (cost per operation).
"""

from __future__ import annotations

from typing import Any

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, Meter

from .semconv import (
    METRIC_COST_PER_OP,
    METRIC_COST_TOTAL,
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
        self._input_token_counter: Counter = m.create_counter(
            name=METRIC_TOKENS_INPUT,
            unit="tokens",
            description="Cumulative input tokens consumed.",
        )
        self._output_token_counter: Counter = m.create_counter(
            name=METRIC_TOKENS_OUTPUT,
            unit="tokens",
            description="Cumulative output tokens generated.",
        )

    def record(
        self,
        cost: dict[str, float],
        attrs: dict[str, Any],
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        total = cost["total"]
        if total > 0:
            self._cost_counter.add(total, attrs)
            self._cost_histogram.record(total, attrs)
        if input_tokens:
            self._input_token_counter.add(input_tokens, attrs)
        if output_tokens:
            self._output_token_counter.add(output_tokens, attrs)
