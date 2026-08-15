import json
from typing import AsyncIterator

import httpx

from ai_provider_gateway.adapters._http import HttpClientOwner, provider_error
from ai_provider_gateway.entities import (
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
    Money,
    ProviderName,
    TextDelta,
)


class OllamaAdapter(HttpClientOwner):
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None):
        super().__init__(client)
        self._base_url = base_url.rstrip("/")

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        payload = {
            "model": request.model,
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
            "stream": False,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        try:
            response = await self._http_client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return CompletionResult(
                text=data["message"]["content"],
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                provider=ProviderName.OLLAMA,
                model=request.model,
            )
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise provider_error(error) from error

    async def stream(self, request: CompletionRequest) -> AsyncIterator[TextDelta]:
        payload = {
            "model": request.model,
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
            "stream": True,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        try:
            async with self._http_client.stream("POST", f"{self._base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        text = json.loads(line).get("message", {}).get("content")
                        if text:
                            yield TextDelta(text=text)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise provider_error(error) from error

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        embeddings = []
        try:
            for text in request.inputs:
                response = await self._http_client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": request.model, "prompt": text},
                )
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])
            return EmbeddingResult(
                embeddings=embeddings,
                model=request.model,
                provider=ProviderName.OLLAMA,
            )
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise provider_error(error) from error

    def estimate_cost(self, request: CompletionRequest) -> Money:
        """Estimate marginal external API charge, not local compute cost."""
        return Money(cents=0)
