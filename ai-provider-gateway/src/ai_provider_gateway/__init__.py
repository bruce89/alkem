"""Provider-neutral contracts and adapters for chat, embeddings, and costs.

    from ai_provider_gateway import ChatProvider, CompletionRequest, Message
    from ai_provider_gateway.adapters import OpenAIAdapter

    provider: ChatProvider = OpenAIAdapter(api_key="sk-...")
    result = await provider.complete(
        CompletionRequest(model="gpt-4o-mini", messages=[Message(role="user", content="hi")])
    )
"""
from ai_provider_gateway.entities import (
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
    Message,
    Money,
    ProviderName,
    TextDelta,
)
from ai_provider_gateway.errors import (
    AuthenticationError,
    InvalidRequestError,
    ModelUnavailableError,
    ProviderConnectionError,
    ProviderError,
    ProviderResponseError,
    RateLimitError,
)
from ai_provider_gateway.ports import ChatProvider, CostEstimator, EmbeddingProvider

__all__ = [
    "ChatProvider",
    "CostEstimator",
    "EmbeddingProvider",
    "CompletionRequest",
    "CompletionResult",
    "EmbeddingRequest",
    "EmbeddingResult",
    "Message",
    "Money",
    "ProviderName",
    "TextDelta",
    "ProviderError",
    "AuthenticationError",
    "RateLimitError",
    "ModelUnavailableError",
    "InvalidRequestError",
    "ProviderConnectionError",
    "ProviderResponseError",
]

__version__ = "0.1.0"
