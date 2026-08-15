import json
from typing import AsyncIterator, Mapping

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
from ai_provider_gateway.pricing import ModelPricing, estimate_completion_cost


class OpenAIAdapter(HttpClientOwner):
    def __init__(
        self,
        api_key: str | None,
        base_url: str = "https://api.openai.com/v1",
        client: httpx.AsyncClient | None = None,
        pricing_by_model: Mapping[str, ModelPricing] | None = None,
    ):
        super().__init__(client)
        self._api_key = api_key
        self._base_url = base_url
        self._pricing_by_model = dict(pricing_by_model or {})

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        payload = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        try:
            response = await self._http_client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=self._headers()
            )
            response.raise_for_status()
            data = response.json()
            return CompletionResult(
                text=data["choices"][0]["message"]["content"],
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                provider=ProviderName.OPENAI,
                model=request.model,
            )
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise provider_error(error) from error

    async def stream(self, request: CompletionRequest) -> AsyncIterator[TextDelta]:
        payload = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        try:
            async with self._http_client.stream(
                "POST", f"{self._base_url}/chat/completions", json=payload, headers=self._headers()
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[len("data: "):])
                        text = data["choices"][0].get("delta", {}).get("content")
                        if text:
                            yield TextDelta(text=text)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise provider_error(error) from error

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        payload = {"model": request.model, "input": request.inputs}
        try:
            response = await self._http_client.post(
                f"{self._base_url}/embeddings", json=payload, headers=self._headers()
            )
            response.raise_for_status()
            data = response.json()
            return EmbeddingResult(
                embeddings=[item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"])],
                model=request.model,
                provider=ProviderName.OPENAI,
            )
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise provider_error(error) from error

    def estimate_cost(self, request: CompletionRequest) -> Money:
        pricing = self._pricing_by_model.get(request.model)
        if pricing is None:
            raise ValueError(f"No pricing configured for model: {request.model}")
        return estimate_completion_cost(request, pricing)
