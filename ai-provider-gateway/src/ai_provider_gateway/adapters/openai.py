import json
from typing import AsyncIterator

import httpx

from ai_provider_gateway.entities import (
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
    Money,
    ProviderName,
    TextDelta,
)

# Rough per-1K-token pricing (cents), used only for pre-call budget estimation —
# NOT used for final billing. Final cost should come from actual token usage
# in the provider's response (see CompletionResult.input_tokens/output_tokens),
# recorded by whatever cost-tracking layer the consuming application has.
_PRICE_PER_1K_INPUT_CENTS = 0.5
_PRICE_PER_1K_OUTPUT_CENTS = 1.5


class OpenAIAdapter:
    def __init__(self, api_key: str | None, base_url: str = "https://api.openai.com/v1"):
        self._api_key = api_key
        self._base_url = base_url

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        payload = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        return CompletionResult(
            text=data["choices"][0]["message"]["content"],
            input_tokens=data["usage"]["prompt_tokens"],
            output_tokens=data["usage"]["completion_tokens"],
            provider=ProviderName.OPENAI,
            model=request.model,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[TextDelta]:
        payload = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self._base_url}/chat/completions", json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[len("data: "):])
                        text = data["choices"][0].get("delta", {}).get("content")
                        if text:
                            yield TextDelta(text=text)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        payload = {"model": request.model, "input": request.inputs}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self._base_url}/embeddings", json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        return EmbeddingResult(
            embeddings=[item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"])],
            model=request.model,
            provider=ProviderName.OPENAI,
        )

    def estimate_cost(self, request: CompletionRequest) -> Money:
        approx_input_tokens = sum(len(m.content) for m in request.messages) // 4
        cents = (approx_input_tokens / 1000) * _PRICE_PER_1K_INPUT_CENTS
        cents += (request.max_tokens / 1000) * _PRICE_PER_1K_OUTPUT_CENTS
        return Money(cents=round(cents * 100))
