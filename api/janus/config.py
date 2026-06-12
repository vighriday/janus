"""Runtime configuration. Reads from environment / .env, never holds secrets in code."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # Auth is keyless throughout — DefaultAzureCredential. No API keys in config.

    # Azure AI Search (Foundry IQ)
    azure_search_endpoint: str = ""
    azure_search_knowledge_base: str = "janus-decisions-kb"
    azure_search_knowledge_source: str = "janus-decisions-ks"
    azure_search_api_version: str = "2026-05-01-preview"

    # Corpus blob source (keyless via search service managed identity)
    azure_storage_account: str = ""
    azure_storage_container: str = "corpus"
    azure_storage_resource_id: str = ""

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_groundedness_deployment: str = "gpt-4o"
    """gpt-4o for Content Safety groundedness reasoning mode (gpt-4o-mini isn't supported there)."""
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2024-10-21"

    # Content Safety (groundedness + prompt shields are REST-only — no typed SDK)
    azure_content_safety_endpoint: str = ""
    content_safety_groundedness_api_version: str = "2024-09-15-preview"
    content_safety_shield_api_version: str = "2024-09-01"

    # Graph is in-process (NetworkX) — no server, no connection config.

    # Observability — OpenTelemetry, dual sink. Both optional: when neither is set
    # the tracer is a no-op and the app boots normally. Local demo points at
    # Phoenix; production sets the App Insights connection string (injected from
    # Key Vault by the managed identity, never a literal here).
    otel_exporter_otlp_endpoint: str = ""
    """Phoenix/OTLP HTTP collector, e.g. http://localhost:6006/v1/traces."""
    applicationinsights_connection_string: str = ""
    """Azure Monitor / Application Insights. Set in the cloud; empty locally."""
    otel_service_name: str = "janus-api"

    # Behaviour
    reranker_threshold: float = 2.5
    """Minimum reranker score for a precedent to count as grounding. Below this, abstain."""

    # Trust-score weights (retrieval, grounding, decisiveness). Sum to 1.0. Exposed
    # so the policy is config, not a magic number scattered across code and UI.
    trust_weight_retrieval: float = 0.3
    trust_weight_grounding: float = 0.4
    trust_weight_decisiveness: float = 0.3
    trust_floor: float = 0.6
    """At/above this composed score the recommendation clears for human review."""

    groundedness_flag_threshold: int = 25
    """Below this grounded-percent, a binary groundedness flag caps trust (a real
    unsupported-claim signal). At or above it, a binary-mode flag with no detailed
    spans is treated as a conservative paraphrase score that lowers the grounding
    component but does not hard-cap the whole score — binary mode (no reasoning
    deployment) flags paraphrased-but-supported lessons too readily to gate on."""

    grounding_supported_floor: float = 0.6
    """Grounding confidence for a lesson the gate considers supported (not hard-
    flagged). Binary `ungroundedPercentage` is not a calibrated magnitude — it
    scores faithful paraphrases low — so a supported lesson earns at least this
    floor for the grounding component, while a truly unsupported one (hard-flagged)
    keeps its low raw score. Reasoning mode would supply a calibrated number and
    retire this floor (roadmap)."""

    # The dependency-concentration knee from the corpus policy (share of a critical
    # flow on one vendor above which the resilience hedge is lost). Single source of
    # truth for the cost model, the causal layer, and the console.
    concentration_knee: float = 0.70


@lru_cache
def get_settings() -> Settings:
    return Settings()
