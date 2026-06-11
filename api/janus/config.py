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

    # Behaviour
    reranker_threshold: float = 2.5
    """Minimum reranker score for a precedent to count as grounding. Below this, abstain."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
