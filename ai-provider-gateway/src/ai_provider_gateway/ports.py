from typing import AsyncIterator, Protocol, runtime_checkable

from ai_provider_gateway.entities import (
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
    Money,
)


@runtime_checkable
class ChatProvider(Protocol):
    """A provider capable of chat completion and text streaming."""

    async def complete(self, request: CompletionRequest) -> CompletionResult: ...

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """A provider capable of generating embeddings."""

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...


@runtime_checkable
class CostEstimator(Protocol):
    """A provider capable of estimating a completion's cost before dispatch."""

    def estimate_cost(self, request: CompletionRequest) -> Money: ...
