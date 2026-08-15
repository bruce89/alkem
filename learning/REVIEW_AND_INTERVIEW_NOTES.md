# Review and Interview Notes

## Provider normalization

> We don't hide provider differences indiscriminately; we normalize the capabilities for which the application needs a stable contract.

Use this when explaining why ALKEM has provider-neutral `CompletionRequest`, `EmbeddingRequest`, `EmbeddingResult`, and `TextDelta`, without claiming that all providers are interchangeable in every respect.

## Adapter boundary

> External provider formats die in the adapter. The domain should not need to know OpenAI SSE, Anthropic event payloads, or Ollama NDJSON.

This connects Ports & Adapters with the Anti-Corruption Layer idea.

## Explicit model selection for embeddings

> The caller selects the embedding model through the request; the adapter translates that decision, but does not own it.

This keeps model selection available to future configuration or orchestration code without creating a registry prematurely.

## Deliberate incompleteness

> We introduced the smallest contract required by a current consumer: text deltas. We deferred lifecycle, usage, tool, and reasoning events until a concrete use case requires them.

This explains scope discipline without presenting missing features as a limitation.

## Capability-specific protocols

> A provider should expose only capabilities it truly supports. A method that exists solely to raise `NotImplementedError` makes the interface syntactically complete but semantically dishonest.

See `docs/DESIGN_AND_LEARNING_NOTES.md` for the longer explanation of interface segregation and substitutability.
