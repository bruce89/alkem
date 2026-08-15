"""Small, explicit model pricing configuration for pre-call estimates."""

from dataclasses import dataclass

from ai_provider_gateway.entities import CompletionRequest, Money

_TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class ModelPricing:
    """Integer-cent rates per one million input and output tokens."""

    input_cents_per_million_tokens: int
    output_cents_per_million_tokens: int

    def __post_init__(self) -> None:
        if self.input_cents_per_million_tokens < 0 or self.output_cents_per_million_tokens < 0:
            raise ValueError("Model pricing rates cannot be negative")


def estimate_completion_cost(request: CompletionRequest, pricing: ModelPricing) -> Money:
    """Estimate in whole cents, rounding a non-integral total up once."""
    estimated_input_tokens = sum(len(message.content) for message in request.messages) // 4
    total_cents_per_million = (
        estimated_input_tokens * pricing.input_cents_per_million_tokens
        + request.max_tokens * pricing.output_cents_per_million_tokens
    )
    cents = (total_cents_per_million + _TOKENS_PER_MILLION - 1) // _TOKENS_PER_MILLION
    return Money(cents=cents)
