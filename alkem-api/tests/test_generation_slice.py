import json

import httpx
import pytest

import ai_provider_gateway.adapters._http as http_helpers
from ai_provider_gateway import ProviderName
from alkem_api import create_app
from alkem_core import AIEngine, ModelConfig


@pytest.mark.asyncio
async def test_http_request_reaches_provider_through_the_core(monkeypatch) -> None:
    provider_requests: list[httpx.Request] = []

    def provider_handler(request: httpx.Request) -> httpx.Response:
        provider_requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "end-to-end answer"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            },
        )

    provider_client = httpx.AsyncClient(transport=httpx.MockTransport(provider_handler))
    engine = AIEngine(
        [ModelConfig(model="configured-model", provider=ProviderName.OPENAI, api_key="test-key")]
    )
    api_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(engine)),
        base_url="http://testserver",
    )
    monkeypatch.setattr(http_helpers.httpx, "AsyncClient", lambda **kwargs: provider_client)

    async with engine:
        async with api_client:
            response = await api_client.post(
                "/v1/generations",
                json={
                    "model": "configured-model",
                    "messages": [{"role": "user", "content": "hello"}],
                    "max_tokens": 32,
                    "temperature": 0.1,
                },
            )

    assert response.status_code == 200
    assert response.json() == {
        "text": "end-to-end answer",
        "model": "configured-model",
        "provider": "OPENAI",
        "usage": {"input_tokens": 7, "output_tokens": 3},
    }
    assert len(provider_requests) == 1
    assert provider_requests[0].url.path == "/v1/chat/completions"
    assert json.loads(provider_requests[0].content) == {
        "model": "configured-model",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 32,
        "temperature": 0.1,
    }
    assert provider_client.is_closed
