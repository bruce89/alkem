# alkem-api

The HTTP adapter for ALKEM's first end-to-end AI generation slice.

It currently exposes:

- `GET /health` for process liveness;
- `POST /v1/generations` for one non-streaming model call;
- validated Pydantic transport contracts;
- explicit translation of core and provider failures at the HTTP boundary.

`create_app(engine)` receives a caller-owned engine. This keeps environment
configuration and resource lifecycle out of the transport adapter. A future
composition root can own those concerns without changing this boundary.
