"""Tests for provider capability contracts and adapter-specific behavior."""

import json
from pathlib import Path

import httpx
import pytest
import ai_provider_gateway.adapters._http as http_helpers
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
    AuthenticationError,
    InvalidRequestError,
    ModelUnavailableError,
    ProviderConnectionError,
    ProviderError,
    ProviderResponseError,
    RateLimitError,
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


@pytest.mark.asyncio
async def test_openai_embed_forwards_model_preserves_order_and_returns_metadata():
    calls: list[dict] = []
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAIAdapter(api_key="test-key", client=client).embed(
            EmbeddingRequest(model="requested-openai-model", inputs=["first", "second"])
        )

    assert calls[0] == {"model": "requested-openai-model", "input": ["first", "second"]}
    assert result.embeddings == [[1.0], [2.0]]
    assert result.model == "requested-openai-model"
    assert result.provider == ProviderName.OPENAI


@pytest.mark.asyncio
async def test_ollama_embed_forwards_model_preserves_order_and_returns_metadata():
    calls: list[dict] = []
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"embedding": [float(len(calls))]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OllamaAdapter(base_url="http://localhost:11434", client=client).embed(
            EmbeddingRequest(model="requested-ollama-model", inputs=["first", "second"])
        )

    assert calls == [
        {"model": "requested-ollama-model", "prompt": "first"},
        {"model": "requested-ollama-model", "prompt": "second"},
    ]
    assert result.embeddings == [[1.0], [2.0]]
    assert result.model == "requested-ollama-model"
    assert result.provider == ProviderName.OLLAMA


def test_adapters_do_not_hardcode_embedding_models():
    assert "text-embedding-3-small" not in Path(openai_module.__file__).read_text()
    assert "nomic-embed-text" not in Path(ollama_module.__file__).read_text()


def test_normalized_errors_share_a_provider_error_base_class():
    for error_type in (
        AuthenticationError,
        RateLimitError,
        ModelUnavailableError,
        InvalidRequestError,
        ProviderConnectionError,
        ProviderResponseError,
    ):
        assert issubclass(error_type, ProviderError)


def completion_response() -> dict:
    return {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }


@pytest.mark.asyncio
async def test_injected_client_is_reused_and_not_closed_by_adapter():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=completion_response())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIAdapter(api_key="test-key", client=client)

    await adapter.complete(CompletionRequest(model="model", messages=[]))
    await adapter.complete(CompletionRequest(model="model", messages=[]))
    await adapter.aclose()

    assert len(requests) == 2
    assert not client.is_closed
    await client.aclose()


@pytest.mark.asyncio
async def test_adapter_context_manager_does_not_close_an_injected_client():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=completion_response())))

    async with OpenAIAdapter(api_key="test-key", client=client) as adapter:
        await adapter.complete(CompletionRequest(model="model", messages=[]))

    assert not client.is_closed
    await client.aclose()


@pytest.mark.asyncio
async def test_adapter_owned_client_can_be_explicitly_closed(monkeypatch):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=completion_response())))
    monkeypatch.setattr(http_helpers.httpx, "AsyncClient", lambda **kwargs: client)
    adapter = OpenAIAdapter(api_key="test-key")

    await adapter.complete(CompletionRequest(model="model", messages=[]))
    assert not client.is_closed

    await adapter.aclose()
    assert client.is_closed


@pytest.mark.asyncio
async def test_adapter_context_manager_closes_an_owned_client(monkeypatch):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=completion_response())))
    monkeypatch.setattr(http_helpers.httpx, "AsyncClient", lambda **kwargs: client)

    async with OpenAIAdapter(api_key="test-key") as adapter:
        await adapter.complete(CompletionRequest(model="model", messages=[]))

    assert client.is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, AuthenticationError),
        (429, RateLimitError),
        (400, InvalidRequestError),
        (404, ModelUnavailableError),
    ],
)
async def test_http_status_failures_are_normalized(status_code, expected_error):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status_code)))
    adapter = OpenAIAdapter(api_key="test-key", client=client)

    with pytest.raises(expected_error) as error:
        await adapter.complete(CompletionRequest(model="model", messages=[]))

    assert not isinstance(error.value, httpx.HTTPError)
    await client.aclose()


@pytest.mark.asyncio
async def test_transport_failure_is_normalized_to_provider_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaAdapter(base_url="http://localhost:11434", client=client)

    with pytest.raises(ProviderConnectionError) as error:
        await adapter.complete(CompletionRequest(model="model", messages=[]))

    assert not isinstance(error.value, httpx.HTTPError)
    await client.aclose()


@pytest.mark.asyncio
async def test_malformed_success_response_is_normalized_to_provider_response_error():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    adapter = AnthropicAdapter(api_key="test-key", client=client)

    with pytest.raises(ProviderResponseError) as error:
        await adapter.complete(CompletionRequest(model="model", messages=[]))

    assert not isinstance(error.value, httpx.HTTPError)
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_stream_emits_normalized_ordered_text_deltas():
    content = '\n'.join([
        'data: {"choices": [{"delta": {"role": "assistant"}}]}',
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"choices": [{"delta": {"content": ""}}]}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
        "data: [DONE]",
    ])
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=content))) as client:
        deltas = [delta async for delta in OpenAIAdapter(api_key="test-key", client=client).stream(CompletionRequest(model="model", messages=[]))]

    assert deltas == [TextDelta("Hello"), TextDelta(" world")]


@pytest.mark.asyncio
async def test_anthropic_stream_emits_normalized_ordered_text_deltas():
    content = '\n'.join(
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
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=content))) as client:
        deltas = [delta async for delta in AnthropicAdapter(api_key="test-key", client=client).stream(CompletionRequest(model="model", messages=[]))]

    assert deltas == [TextDelta("Hello"), TextDelta(" world")]


@pytest.mark.asyncio
async def test_ollama_stream_emits_normalized_ordered_text_deltas_and_completion_options():
    calls: list[dict] = []
    content = '\n'.join(
        [
            '{"message": {"role": "assistant", "content": "Hello"}, "done": false}',
            '{"message": {"content": ""}, "done": false}',
            '{"done": true, "prompt_eval_count": 1}',
            '{"message": {"content": " world"}, "done": false}',
        ]
    )
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(200, text=content)
    request = CompletionRequest(model="model", messages=[], temperature=0.25, max_tokens=64)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        deltas = [delta async for delta in OllamaAdapter(base_url="http://localhost:11434", client=client).stream(request)]

    assert deltas == [TextDelta("Hello"), TextDelta(" world")]
    assert calls[0]["options"] == {"temperature": 0.25, "num_predict": 64}
