# ALKEM

ALKEM is a small, production-oriented training and portfolio project for
Applied AI / AI Software Engineering. It favors end-to-end vertical slices,
explicit boundaries, and operational trade-offs over tutorial-sized demos or
premature platform infrastructure.

## Current packages

- `ai-provider-gateway`: provider-neutral async chat, streaming, embedding,
  error, and cost contracts with OpenAI, Anthropic, and Ollama adapters.
- `alkem-core`: the application layer that owns explicit model selection and
  keeps adapter construction away from consumers.
- `alkem-api`: a thin FastAPI transport adapter for the first non-streaming
  generation slice.

The dependency direction is:

```text
HTTP client -> alkem-api -> alkem-core -> ai-provider-gateway -> providers
```

## Local setup

Using Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e '.\ai-provider-gateway[dev]' -e '.\alkem-core[dev]' -e '.\alkem-api[dev]'
.\.venv\Scripts\python -m pytest ai-provider-gateway\tests alkem-core\tests alkem-api\tests -q
```

## Current milestone

The first HTTP inference boundary is scaffolded and tested through an injected
generation service.

Not yet included: authentication, streaming over HTTP, retry policy,
observability, Docker, persistence, RAG, tool execution, or agents.
