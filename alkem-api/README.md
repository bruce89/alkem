# alkem-api

The HTTP adapter for ALKEM's first end-to-end AI generation slice.

It currently exposes:

- `GET /health` for process liveness;
- `POST /v1/generations` for one non-streaming model call;
- validated Pydantic transport contracts;
- explicit translation of core and provider failures at the HTTP boundary.

`create_app(engine)` receives a caller-owned engine. This keeps environment
configuration and resource lifecycle out of the transport adapter until the
production composition root is implemented.

## Learning tasks

1. Build a composition root that reads validated settings, constructs
   `ModelConfig` values, owns `AIEngine`, and closes it with FastAPI lifespan.
2. Replace the intentionally coarse `ProviderError -> 502` policy with a
   documented mapping based on retryability and safe client-facing details.
3. Add request IDs and structured logs without logging prompts or credentials.
4. Decide and implement a bounded input/context policy. `max_tokens` limits
   output only; it does not prevent oversized prompts.
5. Add API authentication before treating this as a remotely exposed service.

Streaming, retries, Docker, background jobs, RAG, and agent workflows are
deliberately outside this milestone.
