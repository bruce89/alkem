# ai-provider-gateway

A provider-agnostic gateway for calling OpenAI, Anthropic, and Ollama without
application code importing vendor SDKs directly.

```python
from ai_provider_gateway import ChatProvider, CompletionRequest, Message
from ai_provider_gateway.adapters import OpenAIAdapter

provider: ChatProvider = OpenAIAdapter(api_key="sk-...")
result = await provider.complete(
    CompletionRequest(
        model="gpt-4o-mini",
        messages=[Message(role="user", content="Say hi in 3 words")],
    )
)
print(result.text, result.input_tokens, result.output_tokens)
```

Swap the adapter while retaining the same chat contract:

```python
from ai_provider_gateway.adapters import AnthropicAdapter, OllamaAdapter

provider = AnthropicAdapter(api_key="sk-ant-...")
# or, fully local:
provider = OllamaAdapter(base_url="http://localhost:11434")
```

## Capabilities

Providers implement only the capabilities they support:

- `ChatProvider`: `complete()` and `stream()`
- `EmbeddingProvider`: `embed(EmbeddingRequest)`
- `CostEstimator`: `estimate_cost()`

`OpenAIAdapter` and `OllamaAdapter` currently provide chat, embeddings, and
cost estimation. `AnthropicAdapter` currently provides chat and cost
estimation, but not embeddings.

## Streaming

```python
async for chunk in provider.stream(request):
    print(chunk.text, end="", flush=True)
```

Streaming yields provider-neutral `TextDelta` values. Provider-specific SSE
and NDJSON payloads remain inside their adapters.

## HTTP clients and errors

Adapters accept an optional `httpx.AsyncClient` for connection reuse and tests.
Callers retain ownership of an injected client. Without one, an adapter lazily
creates a reusable client; close it with `await adapter.aclose()` or use the
adapter as an async context manager.

Provider calls raise provider-neutral errors instead of raw HTTP exceptions:
`AuthenticationError`, `RateLimitError`, `ModelUnavailableError`,
`InvalidRequestError`, `ProviderConnectionError`, and `ProviderResponseError`.

## Cost estimation

```python
from ai_provider_gateway import CostEstimator

estimator: CostEstimator = OpenAIAdapter(api_key="sk-...")
estimated = estimator.estimate_cost(request)
if estimated.cents > budget_remaining_cents:
    raise BudgetExceeded()
```

`estimate_cost()` is a rough pre-call estimate. Use the token counts returned
on `CompletionResult` for post-call accounting.

## Adding a provider

Implement only the capabilities the provider actually supports:

```python
class MyChatProvider:
    async def complete(self, request: CompletionRequest) -> CompletionResult: ...
    async def stream(self, request: CompletionRequest): ...

class MyEmbeddingProvider:
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...

class MyCostEstimator:
    def estimate_cost(self, request: CompletionRequest) -> Money: ...
```

Each capability is a structural Python `Protocol`: no inheritance,
registration, or plugin system is required.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT. See [LICENSE](./LICENSE).
