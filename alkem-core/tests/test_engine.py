import httpx
import pytest

import ai_provider_gateway.adapters._http as http_helpers
from ai_provider_gateway import Message, ProviderName
from ai_provider_gateway.adapters import AnthropicAdapter, OllamaAdapter, OpenAIAdapter
from alkem_core import AIEngine, ModelConfig, ModelNotConfiguredError


def test_engine_constructs_the_configured_provider_without_exposing_it_to_consumers():
    engine = AIEngine(
        [
            ModelConfig(model="openai-model", provider=ProviderName.OPENAI, api_key="secret"),
            ModelConfig(model="anthropic-model", provider=ProviderName.ANTHROPIC, api_key="secret"),
            ModelConfig(model="local-model", provider=ProviderName.OLLAMA),
        ]
    )

    assert isinstance(engine._providers["openai-model"], OpenAIAdapter)
    assert isinstance(engine._providers["anthropic-model"], AnthropicAdapter)
    assert isinstance(engine._providers["local-model"], OllamaAdapter)
    assert "secret" not in repr(ModelConfig(model="model", provider=ProviderName.OPENAI, api_key="secret"))


@pytest.mark.asyncio
async def test_generate_delegates_to_the_explicitly_configured_model(monkeypatch):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(http_helpers.httpx, "AsyncClient", lambda **kwargs: client)
    engine = AIEngine([ModelConfig(model="configured-model", provider=ProviderName.OPENAI, api_key="secret")])

    result = await engine.generate(
        model="configured-model",
        messages=[Message(role="user", content="hi")],
        max_tokens=12,
        temperature=0.2,
    )

    assert result.text == "hello"
    assert result.model == "configured-model"
    assert result.provider is ProviderName.OPENAI
    assert requests[0].url.path == "/v1/chat/completions"
    await engine.aclose()
    assert client.is_closed


@pytest.mark.asyncio
async def test_engine_context_manager_closes_configured_adapter_clients(monkeypatch):
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "hello"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
            )
        )
    )
    monkeypatch.setattr(http_helpers.httpx, "AsyncClient", lambda **kwargs: client)

    async with AIEngine([ModelConfig(model="configured-model", provider=ProviderName.OPENAI, api_key="secret")]) as engine:
        await engine.generate(model="configured-model", messages=[])
        assert not client.is_closed

    assert client.is_closed


@pytest.mark.asyncio
async def test_generate_rejects_models_not_in_explicit_configuration():
    engine = AIEngine([ModelConfig(model="configured-model", provider=ProviderName.OLLAMA)])

    with pytest.raises(ModelNotConfiguredError, match="No configured model: unknown-model") as error:
        await engine.generate(model="unknown-model", messages=[])

    assert error.value.model == "unknown-model"


def test_engine_rejects_duplicate_model_configuration():
    with pytest.raises(ValueError, match="Model configured more than once: duplicate"):
        AIEngine(
            [
                ModelConfig(model="duplicate", provider=ProviderName.OPENAI),
                ModelConfig(model="duplicate", provider=ProviderName.OLLAMA),
            ]
        )
