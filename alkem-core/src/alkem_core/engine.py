from collections.abc import Sequence
from typing import Self

from ai_provider_gateway import ChatProvider, CompletionRequest, CompletionResult, Message, ProviderName
from ai_provider_gateway.adapters import AnthropicAdapter, OllamaAdapter, OpenAIAdapter

from alkem_core.config import ModelConfig
from alkem_core.errors import ModelNotConfiguredError


class AIEngine:
    """Generate with explicitly configured models without exposing adapters to consumers."""

    def __init__(self, models: Sequence[ModelConfig]):
        self._providers: dict[str, ChatProvider] = {}
        for config in models:
            if config.model in self._providers:
                raise ValueError(f"Model configured more than once: {config.model}")
            self._providers[config.model] = self._create_provider(config)

    async def generate(
        self,
        *,
        model: str,
        messages: list[Message],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> CompletionResult:
        provider = self._providers.get(model)
        if provider is None:
            raise ModelNotConfiguredError(model)
        return await provider.complete(
            CompletionRequest(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        )

    async def aclose(self) -> None:
        for provider in self._providers.values():
            close = getattr(provider, "aclose", None)
            if close is not None:
                await close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.aclose()

    @staticmethod
    def _create_provider(config: ModelConfig) -> ChatProvider:
        if config.provider is ProviderName.OPENAI:
            return OpenAIAdapter(
                api_key=config.api_key,
                base_url=config.base_url or "https://api.openai.com/v1",
            )
        if config.provider is ProviderName.ANTHROPIC:
            return AnthropicAdapter(
                api_key=config.api_key,
                base_url=config.base_url or "https://api.anthropic.com/v1",
            )
        if config.provider is ProviderName.OLLAMA:
            return OllamaAdapter(base_url=config.base_url or "http://localhost:11434")
        raise ValueError(f"Unsupported configured provider: {config.provider}")
