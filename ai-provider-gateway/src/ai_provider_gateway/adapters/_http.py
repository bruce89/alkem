"""Internal HTTP lifecycle and exception translation for adapters."""

from typing import Self

import httpx

from ai_provider_gateway.errors import (
    AuthenticationError,
    InvalidRequestError,
    ModelUnavailableError,
    ProviderConnectionError,
    ProviderError,
    ProviderResponseError,
    RateLimitError,
)


class HttpClientOwner:
    """Own a lazily-created client, or borrow a caller-owned client."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self._owns_client = client is None

    @property
    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=None)
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.aclose()


def provider_error(error: Exception) -> ProviderError:
    """Translate HTTP/infrastructure failures without exposing httpx publicly."""
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        message = f"Provider request failed with HTTP {status_code}."
        if status_code in (401, 403):
            return AuthenticationError(message)
        if status_code == 429:
            return RateLimitError(message)
        if status_code in (400, 422):
            return InvalidRequestError(message)
        if status_code == 404:
            return ModelUnavailableError(message)
        return ProviderResponseError(message)
    if isinstance(error, httpx.RequestError):
        return ProviderConnectionError("Provider connection failed.")
    return ProviderResponseError("Provider returned an invalid response.")
