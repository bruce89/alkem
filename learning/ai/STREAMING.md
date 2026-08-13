# Streaming

## What it is

Streaming returns a model response incrementally instead of waiting for the complete response. This improves perceived responsiveness and makes long responses usable while generation is still in progress.

## Why it matters for ALKEM

Streaming is primarily a user-experience concern at the boundary between the provider, core, and client. It may later support chat interfaces, controlled-output modes, and incremental code-review workflows.

## Current gateway state

`ChatProvider` owns both `complete()` and `stream()` because they are two closely related ways to consume chat generation.

The current adapters still expose provider-specific stream payloads. This is intentionally temporary: consumers should eventually receive a provider-neutral stream event, rather than parse OpenAI or Anthropic SSE data or Ollama JSON lines themselves.

## Deferred design work

A later milestone can introduce a normalized event contract, beginning with text deltas. Usage updates and completion events should only be added when a real consumer needs them.

Do not add routing, retries, HTTP lifecycle changes, or a complex event hierarchy merely as part of streaming normalization.

## Questions to study

- Server-Sent Events (SSE) versus newline-delimited JSON.
- Async iterators and cancellation in Python.
- Backpressure and slow clients.
- Partial output, final usage metadata, and terminal events.
- How a local API can relay a normalized stream to a C#/.NET client.
