"""Tests for provider capability contracts and adapter-specific behavior."""

from pathlib import Path

import pytest
import ai_provider_gateway.adapters.anthropic as anthropic_module
import ai_provider_gateway.adapters.ollama as ollama_module
import ai_provider_gateway.adapters.openai as openai_module

from ai_provider_gateway import (
    ChatProvider,
    CompletionRequest,
    CompletionResult,
    CostEstimator,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResult,
    Message,
    ProviderName,
    TextDelta,
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
        yield TextDelta(text=self._canned_text)


class FakeEmbeddingProvider:
    """A minimal embedding-only provider with no network or SDK."""

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=[[0.0] for _ in request.inputs],
            model=request.model,
            provider=ProviderName.OLLAMA,
        )


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

    result = await adapter.embed(EmbeddingRequest(model="fake-model", inputs=["text"]))

    assert result.embeddings == [[0.0]]
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


class FakeResponse:
    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._data


class RecordingAsyncClient:
    def __init__(self, responses: list[FakeResponse], calls: list[dict]):
        self._responses = responses
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def post(self, url: str, json: dict, headers: dict | None = None) -> FakeResponse:
        self._calls.append({"url": url, "json": json, "headers": headers})
        return self._responses.pop(0)


class FakeStreamResponse:
    def __init__(self, lines: list[str]):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    def raise_for_status(self) -> None:
        pass

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class RecordingStreamingClient:
    def __init__(self, response: FakeStreamResponse, calls: list[dict]):
        self._response = response
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    def stream(self, method: str, url: str, json: dict, headers: dict | None = None) -> FakeStreamResponse:
        self._calls.append({"method": method, "url": url, "json": json, "headers": headers})
        return self._response


@pytest.mark.asyncio
async def test_openai_embed_forwards_model_preserves_order_and_returns_metadata(monkeypatch):
    calls: list[dict] = []
    responses = [
        FakeResponse(
            {
                "data": [
                    {"index": 1, "embedding": [2.0]},
                    {"index": 0, "embedding": [1.0]},
                ]
            }
        )
    ]
    monkeypatch.setattr(
        openai_module.httpx,
        "AsyncClient",
        lambda **kwargs: RecordingAsyncClient(responses, calls),
    )

    result = await OpenAIAdapter(api_key="test-key").embed(
        EmbeddingRequest(model="requested-openai-model", inputs=["first", "second"])
    )

    assert calls[0]["json"] == {"model": "requested-openai-model", "input": ["first", "second"]}
    assert result.embeddings == [[1.0], [2.0]]
    assert result.model == "requested-openai-model"
    assert result.provider == ProviderName.OPENAI


@pytest.mark.asyncio
async def test_ollama_embed_forwards_model_preserves_order_and_returns_metadata(monkeypatch):
    calls: list[dict] = []
    responses = [FakeResponse({"embedding": [1.0]}), FakeResponse({"embedding": [2.0]})]
    monkeypatch.setattr(
        ollama_module.httpx,
        "AsyncClient",
        lambda **kwargs: RecordingAsyncClient(responses, calls),
    )

    result = await OllamaAdapter(base_url="http://localhost:11434").embed(
        EmbeddingRequest(model="requested-ollama-model", inputs=["first", "second"])
    )

    assert [call["json"] for call in calls] == [
        {"model": "requested-ollama-model", "prompt": "first"},
        {"model": "requested-ollama-model", "prompt": "second"},
    ]
    assert result.embeddings == [[1.0], [2.0]]
    assert result.model == "requested-ollama-model"
    assert result.provider == ProviderName.OLLAMA


def test_adapters_do_not_hardcode_embedding_models():
    assert "text-embedding-3-small" not in Path(openai_module.__file__).read_text()
    assert "nomic-embed-text" not in Path(ollama_module.__file__).read_text()


@pytest.mark.asyncio
async def test_openai_stream_emits_normalized_ordered_text_deltas(monkeypatch):
    calls: list[dict] = []
    response = FakeStreamResponse(
        [
            'data: {"choices": [{"delta": {"role": "assistant"}}]}',
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": ""}}]}',
            'data: {"choices": [{"delta": {"content": " world"}}]}',
            "data: [DONE]",
        ]
    )
    monkeypatch.setattr(
        openai_module.httpx,
        "AsyncClient",
        lambda **kwargs: RecordingStreamingClient(response, calls),
    )

    deltas = [
        delta
        async for delta in OpenAIAdapter(api_key="test-key").stream(
            CompletionRequest(model="model", messages=[])
        )
    ]

    assert deltas == [TextDelta("Hello"), TextDelta(" world")]


@pytest.mark.asyncio
async def test_anthropic_stream_emits_normalized_ordered_text_deltas(monkeypatch):
    calls: list[dict] = []
    response = FakeStreamResponse(
        [
            "event: message_start",
            'data: {"type": "message_start", "message": {}}',
            "event: content_block_delta",
            'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hello"}}',
            'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": ""}}',
            'data: {"type": "message_delta", "delta": {"stop_reason": "end_turn"}}',
            'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": " world"}}',
        ]
    )
    monkeypatch.setattr(
        anthropic_module.httpx,
        "AsyncClient",
        lambda **kwargs: RecordingStreamingClient(response, calls),
    )

    deltas = [
        delta
        async for delta in AnthropicAdapter(api_key="test-key").stream(
            CompletionRequest(model="model", messages=[])
        )
    ]

    assert deltas == [TextDelta("Hello"), TextDelta(" world")]


@pytest.mark.asyncio
async def test_ollama_stream_emits_normalized_ordered_text_deltas_and_completion_options(monkeypatch):
    calls: list[dict] = []
    response = FakeStreamResponse(
        [
            '{"message": {"role": "assistant", "content": "Hello"}, "done": false}',
            '{"message": {"content": ""}, "done": false}',
            '{"done": true, "prompt_eval_count": 1}',
            '{"message": {"content": " world"}, "done": false}',
        ]
    )
    monkeypatch.setattr(
        ollama_module.httpx,
        "AsyncClient",
        lambda **kwargs: RecordingStreamingClient(response, calls),
    )
    request = CompletionRequest(model="model", messages=[], temperature=0.25, max_tokens=64)

    deltas = [delta async for delta in OllamaAdapter(base_url="http://localhost:11434").stream(request)]

    assert deltas == [TextDelta("Hello"), TextDelta(" world")]
    assert calls[0]["json"]["options"] == {"temperature": 0.25, "num_predict": 64}
