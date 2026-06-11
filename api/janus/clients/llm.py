"""Azure OpenAI chat client (keyless).

Used for the steps where JANUS itself reasons — extracting the lesson, composing
the recommendation. Retrieval and grounding live in their own clients.
"""
from __future__ import annotations

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

from janus.config import get_settings

_SCOPE = "https://cognitiveservices.azure.com/.default"


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        token_provider = get_bearer_token_provider(DefaultAzureCredential(), _SCOPE)
        self.client = AsyncAzureOpenAI(
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_version=self.settings.azure_openai_api_version,
            azure_ad_token_provider=token_provider,
        )

    async def chat_complete(
        self, messages: list[dict], deployment: str | None = None, **kwargs
    ) -> str:
        response = await self.client.chat.completions.create(
            model=deployment or self.settings.azure_openai_chat_deployment,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def close(self) -> None:
        await self.client.close()
