# HTTP Lifecycle, Ownership, and Error Boundaries

## Resource ownership

An object that creates a resource owns the responsibility to close it. An object that receives a resource from its caller borrows it and must not close it.

In the Provider Gateway:

- an adapter without an injected HTTP client lazily creates and owns one;
- an adapter with an injected `httpx.AsyncClient` borrows it;
- `aclose()` and the adapter async context manager close only adapter-owned clients.

This makes lifecycle responsibility explicit and prevents a provider adapter from unexpectedly breaking a caller that shares an HTTP client.

## Dependency injection

Dependency injection here is deliberately small: an adapter constructor accepts an optional HTTP client.

```python
client = httpx.AsyncClient(...)
adapter = OpenAIAdapter(api_key="...", client=client)
```

The caller can choose a configured client in production or a `MockTransport` client in tests. This improves testability without introducing a DI framework, service container, factory, or new application abstraction.

## Connection pooling

`httpx.AsyncClient` maintains connection pools. Reusing one client avoids creating a new pool and connection setup for every completion, embedding, or streaming request.

The important decision is not to design a generic pool manager. It is simply to give each adapter one reusable owned client unless the caller supplies one.

## Error boundaries

The adapter is the boundary between provider/infrastructure failures and the domain-facing contract.

```text
httpx transport or provider response
            ↓
adapter translation
            ↓
ProviderError subclass
```

Consumers catch provider-neutral errors rather than `httpx` exceptions or provider-specific response objects. The gateway currently maps authentication, rate limiting, invalid requests, unavailable models, connection failures, and malformed responses.

The taxonomy is intentionally small. A failure that cannot be classified reliably becomes `ProviderResponseError`; the adapter should not invent a more specific meaning.

## What this does not do

Normalizing failures does not imply retrying, backing off, falling back to another provider, logging, or recovering automatically. Those are application or orchestration policies and remain outside the Provider Gateway.

## Next Provider Gateway task

Milestone 1, Task 5 is cost estimation. It should verify pricing units and calculation consistency without adding routing, automatic optimization, or dynamic pricing infrastructure.
