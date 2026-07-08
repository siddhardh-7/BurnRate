"""Tests for BurnrateSpanProcessor span enrichment."""

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from burnrate import BurnrateSpanProcessor
from burnrate.semconv import (
    GEN_AI_USAGE_COST_CURRENCY,
    GEN_AI_USAGE_COST_INPUT,
    GEN_AI_USAGE_COST_OUTPUT,
    GEN_AI_USAGE_COST_TOTAL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
)


@pytest.fixture
def exporter_and_tracer():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(BurnrateSpanProcessor())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    return exporter, tracer


def test_cost_attrs_set_on_genai_span(exporter_and_tracer):
    exporter, tracer = exporter_and_tracer
    with tracer.start_as_current_span("chat gpt-4o") as span:
        span.set_attribute("gen_ai.request.model", "gpt-4o")
        span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, 1_000_000)
        span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, 1_000_000)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs[GEN_AI_USAGE_COST_TOTAL] == pytest.approx(12.50, rel=1e-4)
    assert attrs[GEN_AI_USAGE_COST_INPUT] == pytest.approx(2.50, rel=1e-4)
    assert attrs[GEN_AI_USAGE_COST_OUTPUT] == pytest.approx(10.00, rel=1e-4)
    assert attrs[GEN_AI_USAGE_COST_CURRENCY] == "USD"


def test_zero_token_spans_skipped(exporter_and_tracer):
    exporter, tracer = exporter_and_tracer
    with tracer.start_as_current_span("http.get") as span:
        span.set_attribute("http.method", "GET")

    spans = exporter.get_finished_spans()
    assert GEN_AI_USAGE_COST_TOTAL not in (spans[0].attributes or {})


def test_unknown_model_does_not_crash(exporter_and_tracer):
    exporter, tracer = exporter_and_tracer
    with tracer.start_as_current_span("chat unknown") as span:
        span.set_attribute("gen_ai.request.model", "mystery-model-9000")
        span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, 100)
        span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, 100)

    spans = exporter.get_finished_spans()
    assert spans[0].attributes[GEN_AI_USAGE_COST_TOTAL] == 0.0


def test_response_model_takes_precedence(exporter_and_tracer):
    exporter, tracer = exporter_and_tracer
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute("gen_ai.request.model", "gpt-4o")
        span.set_attribute("gen_ai.response.model", "gpt-4o-mini")  # cheaper actual model
        span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, 1_000_000)
        span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, 1_000_000)

    spans = exporter.get_finished_spans()
    total = spans[0].attributes[GEN_AI_USAGE_COST_TOTAL]
    assert total == pytest.approx(0.75, rel=1e-4)  # gpt-4o-mini rate
