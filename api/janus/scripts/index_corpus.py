"""Build the Foundry IQ knowledge base over the synthetic corpus.

Creates a file knowledge source (uploads the corpus directly — no Blob, no
hand-built index), then a knowledge base that wraps it with the embedding model
and the gpt-4o-mini planner. Idempotent: existing files are cleared before
re-upload so re-runs don't accumulate duplicates.

Run once after provisioning:  uv run python -m janus.scripts.index_corpus
Keyless — needs `az login` with the Search data-plane + OpenAI roles.
"""
from __future__ import annotations

import logging
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient

from janus.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("index_corpus")

_CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "corpus"
# Extensions the file knowledge source accepts and that carry decision content.
_EXTS = {".md", ".csv"}


def _models():
    # Import here so a missing/renamed class fails loudly at run time with a clear
    # message rather than at module import.
    from azure.search.documents.indexes.models import (
        AzureBlobKnowledgeSource,
        AzureBlobKnowledgeSourceParameters,
        AzureOpenAIVectorizerParameters,
        KnowledgeBase,
        KnowledgeBaseAzureOpenAIModel,
        KnowledgeRetrievalLowReasoningEffort,
        KnowledgeSourceAzureOpenAIVectorizer,
        KnowledgeSourceIngestionParameters,
        KnowledgeSourceReference,
    )

    return locals()


def main() -> None:
    s = get_settings()
    m = _models()
    client = SearchIndexClient(endpoint=s.azure_search_endpoint, credential=DefaultAzureCredential())

    # 1. Blob knowledge source with integrated vectorization. Keyless: the
    #    connection string carries only the storage ResourceId, so the search
    #    service authenticates to the blob with its managed identity (no key).
    vectorizer = m["KnowledgeSourceAzureOpenAIVectorizer"](
        azure_open_ai_parameters=m["AzureOpenAIVectorizerParameters"](
            resource_url=s.azure_openai_endpoint,
            deployment_name=s.azure_openai_embedding_deployment,
            model_name=s.azure_openai_embedding_deployment,
        )
    )
    ingestion = m["KnowledgeSourceIngestionParameters"](embedding_model=vectorizer)
    ks = m["AzureBlobKnowledgeSource"](
        name=s.azure_search_knowledge_source,
        description="Northwind Logistics synthetic decision history.",
        azure_blob_parameters=m["AzureBlobKnowledgeSourceParameters"](
            connection_string=f"ResourceId={s.azure_storage_resource_id};",
            container_name=s.azure_storage_container,
            ingestion_parameters=ingestion,
        ),
    )
    client.create_or_update_knowledge_source(knowledge_source=ks)
    log.info("knowledge source ready: %s (blob: %s/%s)",
             s.azure_search_knowledge_source, s.azure_storage_account, s.azure_storage_container)

    # 3. Knowledge base over the source: planner model + answer synthesis.
    kb = m["KnowledgeBase"](
        name=s.azure_search_knowledge_base,
        description="JANUS decision-history knowledge base.",
        knowledge_sources=[m["KnowledgeSourceReference"](name=s.azure_search_knowledge_source)],
        output_mode="answerSynthesis",
        answer_instructions=(
            "Cite the ref_id for every claim. If there is no analogous past "
            "decision, respond 'I do not know'."
        ),
        models=[
            m["KnowledgeBaseAzureOpenAIModel"](
                azure_open_ai_parameters=m["AzureOpenAIVectorizerParameters"](
                    resource_url=s.azure_openai_endpoint,
                    deployment_name=s.azure_openai_chat_deployment,
                    model_name=s.azure_openai_chat_deployment,
                )
            )
        ],
        retrieval_reasoning_effort=m["KnowledgeRetrievalLowReasoningEffort"](),
    )
    client.create_or_update_knowledge_base(kb)
    log.info("knowledge base ready: %s", s.azure_search_knowledge_base)


if __name__ == "__main__":
    main()
