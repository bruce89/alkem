"""Provider-neutral failures exposed by gateway adapters."""


class ProviderError(Exception):
    """Base class for failures encountered while invoking a provider."""


class AuthenticationError(ProviderError):
    """The provider rejected the supplied credentials."""


class RateLimitError(ProviderError):
    """The provider rejected the request because of rate limiting."""


class ModelUnavailableError(ProviderError):
    """The requested model was unavailable or could not be found."""


class InvalidRequestError(ProviderError):
    """The provider rejected the request as invalid."""


class ProviderConnectionError(ProviderError):
    """The provider could not be reached or the connection failed."""


class ProviderResponseError(ProviderError):
    """The provider returned an unsuccessful or malformed response."""
