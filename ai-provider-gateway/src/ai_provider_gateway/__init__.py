"""
ai-provider-gateway

A single, provider-agnostic interface for calling OpenAI, Anthropic,
Ollama (local/self-hosted), and — trivially, by adding one more adapter —
any other LLM vendor, without your application code ever importing a
vendor SDK directly.

    from ai_provider_gateway import AIProviderPort, CompletionRequest, Message
    from ai_provider_gateway.adapters import OpenAIAdapter, AnthropicAdapter, OllamaAdapter

    provider: AIProviderPort = OpenAIAdapter(api_key="sk-...")
    result = await provider.complete(
        CompletionRequest(model="gpt-4o-mini", messages=[Message(role="user", content="hi")])
    )

Swap `OpenAIAdapter` for `AnthropicAdapter(api_key=...)` or
`OllamaAdapter(base_url="http://localhost:11434")` — same call site, same
`CompletionResult` shape, zero other code changes. That's the whole point.
"""
from ai_provider_gateway.entities import (
    CompletionRequest,
    CompletionResult,
    Message,
    Money,
    ProviderName,
)
from ai_provider_gateway.ports import AIProviderPort

__all__ = [
    "AIProviderPort",
    "CompletionRequest",
    "CompletionResult",
    "Message",
    "Money",
    "ProviderName",
]

__version__ = "0.1.0"
