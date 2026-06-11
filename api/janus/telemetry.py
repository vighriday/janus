"""OpenTelemetry wiring — the observability layer.

A single tracer provider with a dual sink, both optional:

  - a local OTLP collector (Arize Phoenix) for the on-camera trace UI, and
  - Azure Monitor / Application Insights for the production sink.

Neither is required: with no endpoint and no connection string configured the
provider is still installed but exports nothing, so the app boots and runs
identically with or without a collector. The OpenAI client is auto-instrumented
via OpenInference so the retrieval -> lesson reasoning chain shows up as spans.

Setup is idempotent and never raises into the request path — an observability
backend being down must never take the guardrail down.
"""
from __future__ import annotations

import logging

from janus.config import get_settings

logger = logging.getLogger(__name__)

_CONFIGURED = False


def setup_telemetry() -> None:
    """Install the tracer provider and exporters. Safe to call more than once."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    s = get_settings()
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(
            resource=Resource.create({"service.name": s.otel_service_name})
        )

        exporters = 0
        if s.otel_exporter_otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=s.otel_exporter_otlp_endpoint))
            )
            exporters += 1
            logger.info("telemetry: OTLP exporter -> %s", s.otel_exporter_otlp_endpoint)

        if s.applicationinsights_connection_string:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            provider.add_span_processor(
                BatchSpanProcessor(
                    AzureMonitorTraceExporter(
                        connection_string=s.applicationinsights_connection_string
                    )
                )
            )
            exporters += 1
            logger.info("telemetry: Azure Monitor exporter configured")

        trace.set_tracer_provider(provider)

        # Auto-instrument the OpenAI client so model calls (lesson, levers) are spans.
        try:
            from openinference.instrumentation.openai import OpenAIInstrumentor

            OpenAIInstrumentor().instrument(tracer_provider=provider)
        except Exception:  # pragma: no cover - instrumentation is best-effort
            logger.warning("telemetry: OpenAI instrumentation unavailable", exc_info=True)

        if exporters == 0:
            logger.info("telemetry: no exporter configured; spans are recorded but not shipped")
    except Exception:  # pragma: no cover - observability must never break the app
        logger.warning("telemetry: setup failed; continuing without tracing", exc_info=True)


def tracer():
    """Return the JANUS tracer (a no-op tracer if setup was skipped/failed)."""
    from opentelemetry import trace

    return trace.get_tracer("janus")
