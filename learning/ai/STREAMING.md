# Streaming

## What it is

A normal request/response call waits for the complete model response. Streaming returns that response incrementally instead. This improves perceived responsiveness and makes long responses usable while generation is still in progress.

## Why it matters for ALKEM

Streaming is primarily a user-experience concern at the boundary between the provider, core, and client. It may later support chat interfaces, controlled-output modes, and incremental code-review workflows.

## Current gateway state

`ChatProvider` owns both `complete()` and `stream()` because they are two closely related ways to consume chat generation.

The gateway now exposes a minimal provider-neutral `TextDelta` contract. Consumers do not parse provider wire formats: OpenAI and Anthropic use Server-Sent Events (SSE), while Ollama uses newline-delimited JSON (NDJSON).

## Deferred design work

A later milestone can introduce richer normalized events when a real consumer needs them. Usage updates, completion events, tool deltas, reasoning events, and `StreamStarted` are deliberately not represented yet.

Do not add routing, retries, HTTP lifecycle changes, or a complex event hierarchy merely as part of streaming normalization.

## Questions to study

- Server-Sent Events (SSE) versus newline-delimited JSON.
- Async iterators and cancellation in Python.
- Backpressure and slow clients.
- Partial output, final usage metadata, and terminal events.
- How a local API can relay a normalized stream to a C#/.NET client.
