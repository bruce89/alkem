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


class OllamaAdapter:
    """Local/self-hosted models via Ollama. Zero per-token cost — this is
    the adapter that proves the provider abstraction is real: a client with
    strict data-residency requirements can run 100% of their AI workload
    on-prem behind the same provider capability contracts.
    """

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        payload = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "stream": False,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        return CompletionResult(
            text=data["message"]["content"],
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            provider=ProviderName.OLLAMA,
            model=request.model,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[TextDelta]:
        payload = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "stream": True,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        text = json.loads(line).get("message", {}).get("content")
                        if text:
                            yield TextDelta(text=text)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        embeddings = []
        async with httpx.AsyncClient(timeout=60) as client:
            for text in request.inputs:
                resp = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": request.model, "prompt": text},
                )
                resp.raise_for_status()
                embeddings.append(resp.json()["embedding"])
        return EmbeddingResult(
            embeddings=embeddings,
            model=request.model,
            provider=ProviderName.OLLAMA,
        )

    def estimate_cost(self, request: CompletionRequest) -> Money:
        # Self-hosted: no per-call marginal API cost. Compute cost still
        # exists (GPU time) but is tracked as infra cost, not per-invocation
        # AI cost — see cost_tracking module's 'compute' source type.
        return Money(cents=0)
