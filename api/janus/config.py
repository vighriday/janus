"""Runtime configuration. Reads from environment / .env, never holds secrets in code."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # Azure AI Search (Foundry IQ)
    azure_search_endpoint: str = ""
    azure_search_knowledge_base: str = "janus-decisions-kb"
    azure_search_index: str = "janus-decisions-idx"
    azure_search_api_version: str = "2026-05-01-preview"

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2024-10-21"

    # Content Safety
    azure_content_safety_endpoint: str = ""

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "januslocaldev"

    # Behaviour
    reranker_threshold: float = 2.5
    """Minimum reranker score for a precedent to count as grounding. Below this, abstain."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
