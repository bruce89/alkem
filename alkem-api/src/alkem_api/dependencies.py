from typing import Protocol

from ai_provider_gateway import CompletionResult, Message
from fastapi import Request


class GenerationService(Protocol):
    """The smallest application capability required by the HTTP adapter."""

    async def generate(
        self,
        *,
        model: str,
        messages: list[Message],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> CompletionResult: ...


def get_generation_service(request: Request) -> GenerationService:
    return request.app.state.generation_service
