from typing import Annotated, Literal

from ai_provider_gateway import ProviderName
from pydantic import BaseModel, ConfigDict, Field


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: Annotated[str, Field(min_length=1)]


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: Annotated[str, Field(min_length=1)]
    messages: Annotated[list[MessageRequest], Field(min_length=1)]
    max_tokens: Annotated[int, Field(ge=1, le=16_384)] = 1024
    temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.7


class UsageResponse(BaseModel):
    input_tokens: int
    output_tokens: int


class GenerationResponse(BaseModel):
    text: str
    model: str
    provider: ProviderName
    usage: UsageResponse


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorResponse(BaseModel):
    detail: str
