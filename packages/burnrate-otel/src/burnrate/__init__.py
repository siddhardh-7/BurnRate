"""
burnrate-otel — OpenTelemetry cost observability for AI agents.

Fills the gap in the OTel GenAI semantic conventions: token counts exist,
dollar costs don't. Burnrate adds gen_ai.usage.cost.* to every GenAI span
and streams per-agent/task/user cost metrics to SigNoz.

Quick start:

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from burnrate import BurnrateSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(BurnrateSpanProcessor())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
"""

from .metrics import CostMetrics
from .pricing import PricingTable
from .processor import BurnrateSpanProcessor

__all__ = ["BurnrateSpanProcessor", "PricingTable", "CostMetrics"]
__version__ = "0.1.0"
