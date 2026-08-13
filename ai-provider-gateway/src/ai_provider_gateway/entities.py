from dataclasses import dataclass, field
from enum import StrEnum


class ProviderName(StrEnum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    OLLAMA = "OLLAMA"
    AZURE_OPENAI = "AZURE_OPENAI"


@dataclass(frozen=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class CompletionRequest:
    model: str
    messages: list[Message] = field(default_factory=list)
    max_tokens: int = 1024
    temperature: float = 0.7


@dataclass(frozen=True)
class CompletionResult:
    text: str
    input_tokens: int
    output_tokens: int
    provider: ProviderName
    model: str


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class EmbeddingRequest:
    model: str
    inputs: list[str]


@dataclass(frozen=True)
class EmbeddingResult:
    embeddings: list[list[float]]
    model: str
    provider: ProviderName


@dataclass(frozen=True)
class Money:
    cents: int
    currency: str = "USD"

    def __add__(self, other: "Money") -> "Money":
        if other.currency != self.currency:
            raise ValueError("Cannot add Money of different currencies")
        return Money(self.cents + other.cents, self.currency)
