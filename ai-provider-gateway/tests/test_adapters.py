"""Tests for provider capability contracts and adapter-specific behavior."""

import pytest

from ai_provider_gateway import (
    ChatProvider,
    CompletionRequest,
    CompletionResult,
    CostEstimator,
    EmbeddingProvider,
    Message,
    ProviderName,
)
from ai_provider_gateway.adapters import AnthropicAdapter, OllamaAdapter, OpenAIAdapter


def test_openai_estimate_cost_is_positive_and_deterministic():
    adapter = OpenAIAdapter(api_key="unused-for-this-test")
    request = CompletionRequest(model="gpt-4o-mini", messages=[Message(role="user", content="hello world")])

    cost = adapter.estimate_cost(request)

    assert cost.cents > 0
    assert cost.currency == "USD"
    assert adapter.estimate_cost(request) == cost


def test_anthropic_splits_system_message_from_the_rest():
    system, rest = AnthropicAdapter._split_system(
        [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hi"),
        ]
    )
    assert system == "You are a helpful assistant."
    assert rest == [{"role": "user", "content": "Hi"}]


class FakeChatProvider:
    """A minimal chat-only provider with no network or SDK."""

    def __init__(self, canned_text: str = "fake response"):
        self._canned_text = canned_text

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(
            text=self._canned_text,
            input_tokens=1,
            output_tokens=1,
            provider=ProviderName.OLLAMA,
            model=request.model,
        )

    async def stream(self, request: CompletionRequest):
        yield self._canned_text


class FakeEmbeddingProvider:
    """A minimal embedding-only provider with no network or SDK."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]


@pytest.mark.asyncio
async def test_chat_only_provider_is_valid_without_embeddings():
    adapter: ChatProvider = FakeChatProvider(canned_text="hi there")

    result = await adapter.complete(CompletionRequest(model="fake-model", messages=[]))

    assert result.text == "hi there"
    assert isinstance(adapter, ChatProvider)
    assert not isinstance(adapter, EmbeddingProvider)


@pytest.mark.asyncio
async def test_embedding_only_provider_is_valid_without_chat():
    adapter: EmbeddingProvider = FakeEmbeddingProvider()

    assert await adapter.embed(["text"]) == [[0.0]]
    assert isinstance(adapter, EmbeddingProvider)
    assert not isinstance(adapter, ChatProvider)


def test_concrete_adapters_expose_only_supported_capabilities():
    openai = OpenAIAdapter(api_key="unused-for-this-test")
    anthropic = AnthropicAdapter(api_key="unused-for-this-test")
    ollama = OllamaAdapter(base_url="http://localhost:11434")

    for adapter in (openai, anthropic, ollama):
        assert isinstance(adapter, ChatProvider)
        assert isinstance(adapter, CostEstimator)

    for adapter in (openai, ollama):
        assert isinstance(adapter, EmbeddingProvider)

    assert not isinstance(anthropic, EmbeddingProvider)
