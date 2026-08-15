# Boundaries and Contracts

## Transport protocol vs. domain contract

A transport protocol describes how systems exchange bytes and messages. A domain contract describes the stable concepts that the application uses.

For provider streaming:

```text
OpenAI SSE / Anthropic SSE / Ollama NDJSON
                    ↓
             adapter translation
                    ↓
              TextDelta(text)
```

SSE and NDJSON are transport details. `TextDelta` is an ALKEM domain contract.

This distinction matters because application code should depend on what it needs to do—consume generated text—not on how a particular external system serializes that text.

The adapter is the boundary where transport concerns stop. This keeps a wire-format change local to the adapter rather than spreading it through the application.

## SSE, NDJSON, and WebSocket

| Protocol | Shape | Typical fit | Trade-off |
| --- | --- | --- | --- |
| Server-Sent Events (SSE) | Server-to-client event stream over HTTP | Incremental model output and notifications | One-way from server to client; each provider may define its own event payloads |
| Newline-delimited JSON (NDJSON) | One JSON object per line over HTTP | Simple incremental records, such as Ollama output | Framing is simple, but consumers still need to understand each JSON schema |
| WebSocket | Persistent bidirectional connection | Interactive, low-latency two-way communication | More connection/session complexity than a one-way response stream needs |

ALKEM does not choose one of these protocols as a domain concept. An adapter may consume SSE or NDJSON today, and a future local API may choose a transport appropriate for its clients. The internal application contract remains independent.

## General system-design rule

> Normalize the contract the application needs; isolate the protocol that an integration happens to use.

This applies beyond AI: payment gateways, message brokers, file storage, identity providers, and external APIs all have transport and vendor details that should not become accidental domain concepts.

## Questions to study

- How does framing differ between HTTP bodies, SSE, NDJSON, and WebSockets?
- When is a bidirectional protocol genuinely required?
- How do cancellation and backpressure differ across these transports?
- What makes a domain contract stable while an integration protocol evolves?
