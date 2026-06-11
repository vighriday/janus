"""Azure AI Content Safety — prompt shields + groundedness.

Both features are REST-only (the typed azure-ai-contentsafety SDK doesn't expose
them), so this is a thin keyless client: a bearer token from DefaultAzureCredential
against the cognitiveservices scope.

- Prompt Shields screen the proposed action (direct) and the retrieved documents
  (indirect / XPIA) — a poisoned past-decision record is a real attack surface.
- Groundedness checks an extracted lesson against its sources so the pipeline can
  abstain rather than present an ungrounded principle as authoritative.

Verified against the 2024-09-01 (shields) and 2024-09-15-preview (groundedness)
REST contracts.
"""
from __future__ import annotations

import httpx
from azure.identity import DefaultAzureCredential

from janus.config import get_settings

_SCOPE = "https://cognitiveservices.azure.com/.default"
_SHIELD_DOC_LIMIT = 5  # shieldPrompt accepts at most 5 documents per call


class SafetyClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.endpoint = self.settings.azure_content_safety_endpoint.rstrip("/")
        self._credential = DefaultAzureCredential()
        self._client = httpx.AsyncClient(timeout=20.0)

    def _headers(self) -> dict[str, str]:
        token = self._credential.get_token(_SCOPE).token
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def shield_prompt(self, user_prompt: str, documents: list[str] | None = None) -> dict:
        """Screen the action (and up to 5 documents) for injection.

        Returns {"attack": bool, "user_attack": bool, "doc_attacks": [bool]}.
        """
        docs = (documents or [])[:_SHIELD_DOC_LIMIT]
        url = (
            f"{self.endpoint}/contentsafety/text:shieldPrompt"
            f"?api-version={self.settings.content_safety_shield_api_version}"
        )
        res = await self._client.post(
            url, headers=self._headers(), json={"userPrompt": user_prompt, "documents": docs}
        )
        res.raise_for_status()
        body = res.json()
        user_attack = body.get("userPromptAnalysis", {}).get("attackDetected", False)
        doc_attacks = [d.get("attackDetected", False) for d in body.get("documentsAnalysis", [])]
        return {
            "attack": bool(user_attack or any(doc_attacks)),
            "user_attack": user_attack,
            "doc_attacks": doc_attacks,
        }

    async def detect_groundedness(
        self, text: str, sources: list[str], query: str, *, reasoning: bool = False
    ) -> dict:
        """Check a lesson against its sources.

        Returns {"ungrounded": bool, "ungrounded_pct": float, "details": [...]}.
        groundingSources is a list of plain strings; reasoning mode needs a
        supported gpt-4o deployment (see config), so it's opt-in.
        """
        url = (
            f"{self.endpoint}/contentsafety/text:detectGroundedness"
            f"?api-version={self.settings.content_safety_groundedness_api_version}"
        )
        # Trim to the documented limits before calling.
        grounding = [s[:7500] for s in sources][:55]
        payload: dict = {
            "domain": "Generic",
            "task": "QnA",
            "qna": {"query": query[:7500]},
            "text": text[:7500],
            "groundingSources": grounding,
            "reasoning": reasoning,
        }
        if reasoning:
            payload["llmResource"] = {
                "resourceType": "AzureOpenAI",
                "azureOpenAIEndpoint": self.settings.azure_openai_endpoint,
                "azureOpenAIDeploymentName": self.settings.azure_openai_groundedness_deployment,
            }
        res = await self._client.post(url, headers=self._headers(), json=payload)
        res.raise_for_status()
        body = res.json()
        return {
            "ungrounded": body.get("ungroundedDetected", False),
            "ungrounded_pct": body.get("ungroundedPercentage", 0.0),
            "details": body.get("ungroundedDetails", []),
        }

    async def close(self) -> None:
        await self._client.aclose()
