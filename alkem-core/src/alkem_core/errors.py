class AlkemCoreError(Exception):
    """Base class for application-level ALKEM failures."""


class ModelNotConfiguredError(AlkemCoreError):
    """The requested model is not present in the engine configuration."""

    def __init__(self, model: str):
        self.model = model
        super().__init__(f"No configured model: {model}")
