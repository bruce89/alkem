from typing import AsyncIterator

import httpx

from ai_provider_gateway.entities import (
    CompletionRequest,
    CompletionResult,
    Money,
    ProviderName,
)

_PRICE_PER_1K_INPUT_CENTS = 0.3
_PRICE_PER_1K_OUTPUT_CENTS = 1.5


class AnthropicAdapter:
    """Anthropic's Messages API separates the system prompt from the
    message list, unlike OpenAI's single-array format — this translation
    happens HERE, inside the adapter, so nothing above the AIProviderPort
    needs to know Anthropic's wire format differs from OpenAI's.
    """

    def __init__(self, api_key: str | None, base_url: str = "https://api.anthropic.com/v1"):
        self._api_key = api_key
        self._base_url = base_url

    def _headers(self) -> dict:
        return {
            "x-api-key": self._api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    @staticmethod
    def _split_system(messages) -> tuple[str | None, list[dict]]:
        system = None
        rest = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                rest.append({"role": m.role, "content": m.content})
        return system, rest

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        system, rest = self._split_system(request.messages)
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": rest,
            **({"system": system} if system else {}),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self._base_url}/messages", json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        return CompletionResult(
            text="".join(block.get("text", "") for block in data.get("content", [])),
            input_tokens=data["usage"]["input_tokens"],
            output_tokens=data["usage"]["output_tokens"],
            provider=ProviderName.ANTHROPIC,
            model=request.model,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        system, rest = self._split_system(request.messages)
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": rest,
            "stream": True,
            **({"system": system} if system else {}),
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self._base_url}/messages", json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield line[len("data: "):]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Anthropic does not offer a first-party embeddings endpoint at the
        # time of writing; this adapter delegates embeddings to whichever
        # provider is configured as the org's embedding provider (typically
        # OpenAI or a local model via Ollama). Raising here makes that
        # limitation explicit rather than silently wrong.
        raise NotImplementedError(
            "AnthropicAdapter does not support embeddings; configure a separate embedding provider"
        )

    def estimate_cost(self, request: CompletionRequest) -> Money:
        approx_input_tokens = sum(len(m.content) for m in request.messages) // 4
        cents = (approx_input_tokens / 1000) * _PRICE_PER_1K_INPUT_CENTS
        cents += (request.max_tokens / 1000) * _PRICE_PER_1K_OUTPUT_CENTS
        return Money(cents=round(cents * 100))
