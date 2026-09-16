import httpx
import pytest

from ai_provider_gateway import (
    CompletionResult,
    Message,
    ProviderConnectionError,
    ProviderName,
)
from alkem_api import create_app
from alkem_core import ModelNotConfiguredError


class FakeGenerationService:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.error: Exception | None = None

    async def generate(
        self,
        *,
        model: str,
        messages: list[Message],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> CompletionResult:
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        if self.error is not None:
            raise self.error
        return CompletionResult(
            text="normalized answer",
            input_tokens=11,
            output_tokens=4,
            provider=ProviderName.OLLAMA,
            model=model,
        )


def api_client_for(service: FakeGenerationService) -> httpx.AsyncClient:
    app = create_app(service)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.mark.asyncio
async def test_health_is_a_cheap_liveness_check() -> None:
    service = FakeGenerationService()

    async with api_client_for(service) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert service.calls == []


@pytest.mark.asyncio
async def test_generation_validates_and_translates_the_http_contract() -> None:
    service = FakeGenerationService()

    async with api_client_for(service) as client:
        response = await client.post(
            "/v1/generations",
            json={
                "model": "local-model",
                "messages": [{"role": "user", "content": "Explain ports and adapters."}],
                "max_tokens": 200,
                "temperature": 0.2,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "text": "normalized answer",
        "model": "local-model",
        "provider": "OLLAMA",
        "usage": {"input_tokens": 11, "output_tokens": 4},
    }
    assert service.calls == [
        {
            "model": "local-model",
            "messages": [Message(role="user", content="Explain ports and adapters.")],
            "max_tokens": 200,
            "temperature": 0.2,
        }
    ]


@pytest.mark.asyncio
async def test_generation_rejects_invalid_transport_input_before_calling_core() -> None:
    service = FakeGenerationService()

    async with api_client_for(service) as client:
        response = await client.post(
            "/v1/generations",
            json={
                "model": "local-model",
                "messages": [{"role": "tool", "content": "not supported yet"}],
                "max_tokens": 0,
                "unexpected": True,
            },
        )

    assert response.status_code == 422
    assert service.calls == []


@pytest.mark.asyncio
async def test_unknown_model_is_a_safe_client_facing_404() -> None:
    service = FakeGenerationService()
    service.error = ModelNotConfiguredError("missing-model")

    async with api_client_for(service) as client:
        response = await client.post(
            "/v1/generations",
            json={"model": "missing-model", "messages": [{"role": "user", "content": "hello"}]},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Model is not configured: missing-model"}


@pytest.mark.asyncio
async def test_provider_failure_does_not_leak_infrastructure_details() -> None:
    service = FakeGenerationService()
    service.error = ProviderConnectionError("secret internal endpoint failed")

    async with api_client_for(service) as client:
        response = await client.post(
            "/v1/generations",
            json={"model": "local-model", "messages": [{"role": "user", "content": "hello"}]},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "The configured AI provider failed."}
    assert "secret internal endpoint" not in response.text
