"""Foundry IQ retrieval — the one real Microsoft IQ integration.

This is agentic retrieval over an Azure AI Search knowledge base: the service
plans subqueries, runs them, reranks, and (in answer-synthesis mode) returns a
grounded answer with inline [ref_id:N] citations. We parse three things the
pipeline needs: the synthesized answer, the ranked references (with reranker
scores and the source document behind each), and the activity record (the
subqueries the planner generated).

Auth is keyless (DefaultAzureCredential). The preview retrieve path is primary;
if it is unavailable the caller can fall back to the GA extractive path.

Verified against azure-search-documents 12.1.0b2 (REST 2026-05-01-preview).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from azure.identity import DefaultAzureCredential
from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    AzureBlobKnowledgeSourceParams,
    KnowledgeBaseMessage,
    KnowledgeBaseMessageTextContent,
    KnowledgeBaseRetrievalRequest,
    KnowledgeRetrievalLowReasoningEffort,
)

from janus.config import get_settings

logger = logging.getLogger(__name__)

# Sources are handed to the planner as JSON with a ref_id; the answer must cite
# them, and abstain when the evidence isn't there. This instruction is what makes
# the no-precedent path real rather than a hardcoded branch.
_GROUNDING_INSTRUCTION = (
    "The sources are decision records from the organization's history, each with "
    "a ref_id. Answer the question using only these sources and cite the ref_id "
    "for every claim. If the sources do not contain an analogous past decision, "
    "respond exactly with 'I do not know' and do not invent a precedent."
)


def _title_from_snippet(snippet: str) -> str:
    """Pull the `title:` line out of a doc's frontmatter snippet, if present."""
    for line in snippet.splitlines():
        if line.strip().lower().startswith("title:"):
            return line.split(":", 1)[1].strip()
    return ""


def doc_id_from_snippet(snippet: str) -> str:
    """Pull the `doc_id:` line out of a doc's frontmatter snippet, if present."""
    for line in snippet.splitlines():
        if line.strip().lower().startswith("doc_id:"):
            return line.split(":", 1)[1].strip()
    return ""


@dataclass
class Precedent:
    """One retrieved past decision, with the score that decided whether it counts."""

    ref_id: str
    doc_key: str  # the corpus filename (from the blob url), used to join to the graph
    title: str
    content: str
    reranker_score: float | None
    blob_url: str = ""


@dataclass
class RetrievalOutcome:
    """Everything the pipeline reads from one retrieval call."""

    answer: str
    subqueries: list[str] = field(default_factory=list)
    precedents: list[Precedent] = field(default_factory=list)
    abstained: bool = False
    ga_fallback: bool = False


class FoundryRetriever:
    """Calls Foundry IQ agentic retrieval and parses the response for the pipeline."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = KnowledgeBaseRetrievalClient(
            endpoint=self.settings.azure_search_endpoint,
            knowledge_base_name=self.settings.azure_search_knowledge_base,
            credential=DefaultAzureCredential(),
        )

    def retrieve(self, question: str) -> RetrievalOutcome:
        """Run agentic retrieval for a decision question and parse the result."""
        request = KnowledgeBaseRetrievalRequest(
            messages=[
                KnowledgeBaseMessage(
                    role="assistant",
                    content=[KnowledgeBaseMessageTextContent(text=_GROUNDING_INSTRUCTION)],
                ),
                KnowledgeBaseMessage(
                    role="user",
                    content=[KnowledgeBaseMessageTextContent(text=question)],
                ),
            ],
            output_mode="answerSynthesis",
            include_activity=True,
            retrieval_reasoning_effort=KnowledgeRetrievalLowReasoningEffort(),
            knowledge_source_params=[
                AzureBlobKnowledgeSourceParams(
                    knowledge_source_name=self.settings.azure_search_knowledge_source,
                    reranker_threshold=self.settings.reranker_threshold,
                    include_references=True,
                    include_reference_source_data=True,
                )
            ],
        )
        result = self.client.retrieve(request)
        return self._parse(result)

    def _parse(self, result) -> RetrievalOutcome:
        # Synthesized answer: response[0] is the assistant message.
        answer = ""
        if result.response and result.response[0].content:
            answer = (result.response[0].content[0].text or "").strip()

        # Subqueries: pulled from each searchIndex activity record's generated search.
        subqueries: list[str] = []
        for record in result.activity or []:
            if getattr(record, "type", None) == "searchIndex":
                args = getattr(record, "search_index_arguments", None)
                q = getattr(args, "search", None) if args else None
                if q:
                    subqueries.append(q)

        # References: each carries the reranker score and the source behind it.
        # Blob references expose source_data = {uid, blob_url, snippet}; the
        # snippet holds the doc's frontmatter, and the blob_url ends in the
        # corpus filename, which is how we join back to the decision graph.
        precedents: list[Precedent] = []
        for ref in result.references or []:
            data = getattr(ref, "source_data", None) or {}
            blob_url = data.get("blob_url", "") or getattr(ref, "blob_url", "") or ""
            filename = blob_url.rsplit("/", 1)[-1] if blob_url else ""
            snippet = str(data.get("snippet", data.get("content", "")))
            precedents.append(
                Precedent(
                    ref_id=str(getattr(ref, "id", "")),
                    doc_key=filename,
                    title=_title_from_snippet(snippet) or filename,
                    content=snippet,
                    reranker_score=getattr(ref, "reranker_score", None),
                    blob_url=blob_url,
                )
            )

        abstained = not precedents or answer.strip().lower().startswith("i do not know")
        return RetrievalOutcome(
            answer=answer, subqueries=subqueries, precedents=precedents, abstained=abstained
        )

    def close(self) -> None:
        self.client.close()
