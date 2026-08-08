# ai-provider-gateway

A single, provider-agnostic interface for calling OpenAI, Anthropic, Ollama
(local/self-hosted), and Azure OpenAI — without your application code ever
importing a vendor SDK directly.

```python
from ai_provider_gateway import AIProviderPort, CompletionRequest, Message
from ai_provider_gateway.adapters import OpenAIAdapter, AnthropicAdapter, OllamaAdapter

provider: AIProviderPort = OpenAIAdapter(api_key="sk-...")

result = await provider.complete(
    CompletionRequest(
        model="gpt-4o-mini",
        messages=[Message(role="user", content="Say hi in 3 words")],
    )
)
print(result.text, result.input_tokens, result.output_tokens)
```

Swap the adapter, keep everything else identical:

```python
provider = AnthropicAdapter(api_key="sk-ant-...")
# or, fully local, zero API cost:
provider = OllamaAdapter(base_url="http://localhost:11434")
```

Same `CompletionRequest` in, same `CompletionResult` out, regardless of vendor.

## Why

Most projects that call multiple LLM providers end up with vendor SDK calls
scattered across the codebase — each with its own request/response shape,
its own streaming format, its own way of splitting a system prompt from the
message list. Swapping providers, or supporting more than one at once,
means touching business logic everywhere that logic happens to call an LLM.

This library is a small, dependency-light abstraction (built on
[Ports & Adapters / Hexagonal Architecture](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software))
principles) that fixes that: one `Protocol` (`AIProviderPort`), one adapter
per vendor, and application code that only ever depends on the Protocol.

## What's included

- `AIProviderPort` — the interface: `complete()`, `stream()`, `embed()`, `estimate_cost()`
- Adapters: `OpenAIAdapter`, `AnthropicAdapter`, `OllamaAdapter` (Azure OpenAI
  shares OpenAI's wire protocol — parameterize `OpenAIAdapter` with your
  Azure `base_url`/deployment, or open an issue if a dedicated adapter would help)
- Plain dataclasses for requests/results (`CompletionRequest`, `Message`,
  `CompletionResult`, `Money`) — no framework dependency, works in any
  Python project (FastAPI, Django, a CLI script, a Jupyter notebook)

## Install

```bash
pip install ai-provider-gateway   # once published; for now, install from source (see below)
```

From source:

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/ai-provider-gateway
cd ai-provider-gateway
pip install -e ".[dev]"
```

## Streaming

```python
async for chunk in provider.stream(request):
    print(chunk, end="", flush=True)
```

## Cost estimation before you spend anything

```python
estimated = provider.estimate_cost(request)
if estimated.cents > budget_remaining_cents:
    raise BudgetExceeded()
result = await provider.complete(request)  # only dispatch after the check
```

`estimate_cost()` is a rough pre-call estimate (character-based token
approximation); for actual billing, use the real `input_tokens`/`output_tokens`
returned on `CompletionResult` after the call completes.

## Adding a new provider

Implement `AIProviderPort` for the new vendor:

```python
class MyProviderAdapter:
    async def complete(self, request: CompletionRequest) -> CompletionResult: ...
    async def stream(self, request: CompletionRequest): ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    def estimate_cost(self, request: CompletionRequest) -> Money: ...
```

That's the whole contract. No registration step, no plugin system to learn —
it's a Python `Protocol`, so any class with these four methods already
satisfies it (structural typing, not inheritance).

## Testing your own code against this

Because `AIProviderPort` is a `Protocol`, you can write a trivial fake for
your own tests without touching a real API — see `tests/test_adapters.py`
for a `FakeAdapter` example (~15 lines, zero mocking framework needed).

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](./LICENSE).

## Origin

Extracted from the AI provider gateway module of a larger platform project;
published standalone because the abstraction is useful on its own and isn't
tied to anything else in that platform.
