from typing import AsyncIterator, Protocol

from ai_provider_gateway.entities import CompletionRequest, CompletionResult, Money


class AIProviderPort(Protocol):
    """Every vendor (OpenAI, Anthropic, Ollama, Azure OpenAI, ...future ones)
    implements this SAME interface. Application code depends only on this
    Protocol, never on a vendor SDK directly — swapping providers becomes a
    config/DI change instead of a rewrite.
    """

    async def complete(self, request: CompletionRequest) -> CompletionResult: ...

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    def estimate_cost(self, request: CompletionRequest) -> Money:
        """Called BEFORE dispatch so callers (a budget guard, a workflow
        engine, or any cost-aware orchestration layer) can reject a call
        that would blow a budget, rather than finding out after money is
        already spent.
        """
        ...
