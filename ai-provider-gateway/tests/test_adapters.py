"""
These tests deliberately never hit a real network. estimate_cost() is pure
math; the FakeAdapter test demonstrates the actual payoff of designing
against a Protocol — any code written against AIProviderPort can be tested
with a trivial fake, with no vendor SDK, no API key, no mocking framework.
"""
import pytest

from ai_provider_gateway import AIProviderPort, CompletionRequest, CompletionResult, Message, Money, ProviderName
from ai_provider_gateway.adapters import AnthropicAdapter, OpenAIAdapter


def test_openai_estimate_cost_is_positive_and_deterministic():
    adapter = OpenAIAdapter(api_key="unused-for-this-test")
    request = CompletionRequest(model="gpt-4o-mini", messages=[Message(role="user", content="hello world")])

    cost = adapter.estimate_cost(request)

    assert cost.cents > 0
    assert cost.currency == "USD"
    assert adapter.estimate_cost(request) == cost  # deterministic for the same input


def test_anthropic_splits_system_message_from_the_rest():
    system, rest = AnthropicAdapter._split_system(
        [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hi"),
        ]
    )
    assert system == "You are a helpful assistant."
    assert rest == [{"role": "user", "content": "Hi"}]


class FakeAdapter:
    """A minimal AIProviderPort implementation — no network, no SDK.
    This is what any application built against the Protocol gets 'for free'
    in its own test suite.
    """

    def __init__(self, canned_text: str = "fake response"):
        self._canned_text = canned_text

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(
            text=self._canned_text, input_tokens=1, output_tokens=1,
            provider=ProviderName.OLLAMA, model=request.model,
        )

    async def stream(self, request: CompletionRequest):
        yield self._canned_text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]

    def estimate_cost(self, request: CompletionRequest) -> Money:
        return Money(cents=0)


@pytest.mark.asyncio
async def test_fake_adapter_satisfies_the_protocol():
    adapter: AIProviderPort = FakeAdapter(canned_text="hi there")
    result = await adapter.complete(CompletionRequest(model="fake-model", messages=[]))
    assert result.text == "hi there"
