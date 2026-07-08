"""
BurnrateSpanProcessor — the core of the burnrate-otel SDK.

Installs as a standard OTel SpanProcessor. On span end it:
  1. Detects GenAI spans by checking for gen_ai.usage.* attributes.
  2. Resolves the model (gen_ai.response.model > gen_ai.request.model).
  3. Calculates dollar cost via PricingTable.
  4. Enriches the span with gen_ai.usage.cost.* attributes (proposed semconv).
  5. Emits burnrate.cost.usd counter + histogram via CostMetrics.

Usage:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from burnrate import BurnrateSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(BurnrateSpanProcessor())          # cost enrichment
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))  # export
    trace.set_tracer_provider(provider)

That's it. Any span with gen_ai.usage.input_tokens will be cost-enriched.
"""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span

from .metrics import CostMetrics
from .pricing import PricingTable
from .semconv import (
    BURNRATE_AGENT_ID,
    BURNRATE_FEATURE,
    BURNRATE_TASK_ID,
    BURNRATE_USER_ID,
    GEN_AI_AGENT_ID,
    GEN_AI_AGENT_NAME,
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_RESPONSE_MODEL,
    GEN_AI_SYSTEM,
    GEN_AI_USAGE_CACHE_CREATION_INPUT_TOKENS,
    GEN_AI_USAGE_CACHE_READ_INPUT_TOKENS,
    GEN_AI_USAGE_COST_CACHE_CREATION,
    GEN_AI_USAGE_COST_CACHE_READ,
    GEN_AI_USAGE_COST_CURRENCY,
    GEN_AI_USAGE_COST_INPUT,
    GEN_AI_USAGE_COST_OUTPUT,
    GEN_AI_USAGE_COST_PRICING_MODEL,
    GEN_AI_USAGE_COST_REASONING,
    GEN_AI_USAGE_COST_TOTAL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    GEN_AI_USAGE_REASONING_TOKENS,
)

log = logging.getLogger(__name__)


class BurnrateSpanProcessor:
    """
    Drop-in OTel SpanProcessor that enriches GenAI spans with dollar costs
    and emits per-agent / per-task / per-user cost metrics to SigNoz.
    """

    def __init__(
        self,
        pricing_table: PricingTable | None = None,
        cost_metrics: CostMetrics | None = None,
        log_unknown_models: bool = True,
    ) -> None:
        self._pricing = pricing_table or PricingTable()
        self._metrics = cost_metrics or CostMetrics()
        self._log_unknown = log_unknown_models

    # ── SpanProcessor interface ──────────────────────────────────────────────

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        pass

    def _on_ending(self, span: Span) -> None:
        """
        Called by the OTel SDK (v1.26+) with the still-mutable span just before
        it ends. This is the correct hook for writing derived span attributes.
        Also emits cost metrics here so we have all token data available.
        """
        self._enrich(span, span.attributes or {})

    def on_end(self, span: ReadableSpan) -> None:
        """Span is read-only here — enrichment already happened in _on_ending."""
        pass

    def _enrich(self, span: Span, attrs: Any) -> None:
        """Core enrichment logic — called with a mutable span."""
        input_tokens = int(attrs.get(GEN_AI_USAGE_INPUT_TOKENS, 0))
        output_tokens = int(attrs.get(GEN_AI_USAGE_OUTPUT_TOKENS, 0))
        if input_tokens == 0 and output_tokens == 0:
            return

        cache_creation = int(attrs.get(GEN_AI_USAGE_CACHE_CREATION_INPUT_TOKENS, 0))
        cache_read = int(attrs.get(GEN_AI_USAGE_CACHE_READ_INPUT_TOKENS, 0))
        reasoning = int(attrs.get(GEN_AI_USAGE_REASONING_TOKENS, 0))

        model = (
            attrs.get(GEN_AI_RESPONSE_MODEL)
            or attrs.get(GEN_AI_REQUEST_MODEL)
            or ""
        )

        cost = self._pricing.cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
            reasoning_tokens=reasoning,
        )

        if cost.get("unknown_model") and self._log_unknown:
            log.warning(
                "burnrate: unknown model %r — cost set to $0. "
                "Register it via PricingTable.register() or BURNRATE_PRICING_FILE.",
                model,
            )

        # Write cost attributes to span._attributes.
        # OTel SDK sets _attributes._immutable = True BEFORE calling _on_ending,
        # so we temporarily clear the flag, write our derived attrs, then restore it.
        # This is safe: _on_ending runs outside the span's internal lock.
        try:
            a = span._attributes
            was_immutable = getattr(a, "_immutable", False)
            a._immutable = False
            try:
                a[GEN_AI_USAGE_COST_TOTAL] = round(cost["total"], 8)
                a[GEN_AI_USAGE_COST_INPUT] = round(cost["input"], 8)
                a[GEN_AI_USAGE_COST_OUTPUT] = round(cost["output"], 8)
                a[GEN_AI_USAGE_COST_CACHE_CREATION] = round(cost["cache_creation"], 8)
                a[GEN_AI_USAGE_COST_CACHE_READ] = round(cost["cache_read"], 8)
                a[GEN_AI_USAGE_COST_REASONING] = round(cost["reasoning"], 8)
                a[GEN_AI_USAGE_COST_CURRENCY] = "USD"
                a[GEN_AI_USAGE_COST_PRICING_MODEL] = "per_token"
            finally:
                a._immutable = was_immutable
        except Exception:
            pass  # SDK internal API changed — metrics still flow

        # Build metric dimensions for cost attribution
        metric_attrs: dict[str, Any] = {}
        for attr_key, dim in [
            (GEN_AI_SYSTEM, "gen_ai.system"),
            (GEN_AI_OPERATION_NAME, "gen_ai.operation.name"),
            (BURNRATE_AGENT_ID, "burnrate.agent.id"),
            (GEN_AI_AGENT_ID, "burnrate.agent.id"),
            (GEN_AI_AGENT_NAME, "burnrate.agent.name"),
            (BURNRATE_TASK_ID, "burnrate.task.id"),
            (BURNRATE_USER_ID, "burnrate.user.id"),
            (BURNRATE_FEATURE, "burnrate.feature"),
        ]:
            val = attrs.get(attr_key)
            if val and dim not in metric_attrs:
                metric_attrs[dim] = str(val)

        metric_attrs["gen_ai.request.model"] = model or "unknown"

        self._metrics.record(
            cost=cost,
            attrs=metric_attrs,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
        )

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return True
