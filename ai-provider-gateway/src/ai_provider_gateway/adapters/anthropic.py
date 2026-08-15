import json
from typing import AsyncIterator, Mapping

import httpx

from ai_provider_gateway.adapters._http import HttpClientOwner, provider_error
from ai_provider_gateway.entities import CompletionRequest, CompletionResult, Money, ProviderName, TextDelta
from ai_provider_gateway.pricing import ModelPricing, estimate_completion_cost


class AnthropicAdapter(HttpClientOwner):
    def __init__(
        self,
        api_key: str | None,
        base_url: str = "https://api.anthropic.com/v1",
        client: httpx.AsyncClient | None = None,
        pricing_by_model: Mapping[str, ModelPricing] | None = None,
    ):
        super().__init__(client)
        self._api_key = api_key
        self._base_url = base_url
        self._pricing_by_model = dict(pricing_by_model or {})

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
        for message in messages:
            if message.role == "system":
                system = message.content
            else:
                rest.append({"role": message.role, "content": message.content})
        return system, rest

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        system, messages = self._split_system(request.messages)
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
            **({"system": system} if system else {}),
        }
        try:
            response = await self._http_client.post(f"{self._base_url}/messages", json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()
            return CompletionResult(
                text="".join(block.get("text", "") for block in data.get("content", [])),
                input_tokens=data["usage"]["input_tokens"],
                output_tokens=data["usage"]["output_tokens"],
                provider=ProviderName.ANTHROPIC,
                model=request.model,
            )
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise provider_error(error) from error

    async def stream(self, request: CompletionRequest) -> AsyncIterator[TextDelta]:
        system, messages = self._split_system(request.messages)
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
            "stream": True,
            **({"system": system} if system else {}),
        }
        try:
            async with self._http_client.stream("POST", f"{self._base_url}/messages", json=payload, headers=self._headers()) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[len("data: "):])
                        text = data.get("delta", {}).get("text") if data.get("type") == "content_block_delta" else None
                        if text:
                            yield TextDelta(text=text)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise provider_error(error) from error

    def estimate_cost(self, request: CompletionRequest) -> Money:
        pricing = self._pricing_by_model.get(request.model)
        if pricing is None:
            raise ValueError(f"No pricing configured for model: {request.model}")
        return estimate_completion_cost(request, pricing)
