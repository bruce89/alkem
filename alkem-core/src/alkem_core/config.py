from dataclasses import dataclass, field

from ai_provider_gateway import ProviderName


@dataclass(frozen=True)
class ModelConfig:
    """Explicit connection settings for one configured model."""

    model: str
    provider: ProviderName
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None
