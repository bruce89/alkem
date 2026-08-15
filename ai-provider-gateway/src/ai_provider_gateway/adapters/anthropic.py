import json
from typing import AsyncIterator

import httpx

from ai_provider_gateway.adapters._http import HttpClientOwner, provider_error
from ai_provider_gateway.entities import CompletionRequest, CompletionResult, Money, ProviderName, TextDelta

_PRICE_PER_1K_INPUT_CENTS = 0.3
_PRICE_PER_1K_OUTPUT_CENTS = 1.5


class AnthropicAdapter(HttpClientOwner):
    def __init__(
        self,
        api_key: str | None,
        base_url: str = "https://api.anthropic.com/v1",
        client: httpx.AsyncClient | None = None,
    ):
        super().__init__(client)
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
        approx_input_tokens = sum(len(message.content) for message in request.messages) // 4
        cents = (approx_input_tokens / 1000) * _PRICE_PER_1K_INPUT_CENTS
        cents += (request.max_tokens / 1000) * _PRICE_PER_1K_OUTPUT_CENTS
        return Money(cents=round(cents * 100))
