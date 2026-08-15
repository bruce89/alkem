# Provider Boundaries and Normalization

## Boundary normalization

Provider normalization does not mean pretending that OpenAI, Anthropic, and Ollama are identical.

ALKEM normalizes only the capabilities the application needs to consume uniformly. For example, a consumer needs a stable stream of text, so adapters translate SSE or NDJSON payloads into `TextDelta` values. Provider-specific wire formats do not cross the boundary.

## Ports & Adapters / Anti-Corruption Layer

The Provider Gateway is an application of Ports & Adapters. Provider APIs are external systems with their own request shapes, response shapes, event protocols, and failures.

The adapter is also an Anti-Corruption Layer:

```text
provider wire protocol
        ↓
adapter translation
        ↓
ALKEM domain contract
```

External formats should die in the adapter. Domain and application code should not know OpenAI SSE payloads, Anthropic event types, or Ollama NDJSON structures.

## Deliberately incomplete contracts

`TextDelta` is intentionally the smallest useful streaming contract. ALKEM does not yet model `StreamStarted`, `Completed`, usage updates, tool-call deltas, reasoning events, or a large event hierarchy.

This is not an omission by accident. New domain concepts should appear only when a real application consumer requires them.

## Design rule

Normalize stable application needs, not every provider detail.

Provider differences that matter to the application should remain explicit. Differences that are only transport details belong inside adapters.
