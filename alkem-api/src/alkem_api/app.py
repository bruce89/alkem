from ai_provider_gateway import Message, ProviderError
from alkem_core import ModelNotConfiguredError
from fastapi import Depends, FastAPI, HTTPException, status

from alkem_api.contracts import (
    ErrorResponse,
    GenerationRequest,
    GenerationResponse,
    HealthResponse,
    UsageResponse,
)
from alkem_api.dependencies import GenerationService, get_generation_service


def create_app(engine: GenerationService) -> FastAPI:
    """Create an HTTP adapter around a caller-owned generation service."""
    app = FastAPI(title="ALKEM API", version="0.1.0")
    app.state.generation_service = engine

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post(
        "/v1/generations",
        response_model=GenerationResponse,
        responses={
            status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
            status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
        },
        tags=["generation"],
    )
    async def generate(
        request: GenerationRequest,
        service: GenerationService = Depends(get_generation_service),
    ) -> GenerationResponse:
        try:
            result = await service.generate(
                model=request.model,
                messages=[Message(role=message.role, content=message.content) for message in request.messages],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
        except ModelNotConfiguredError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model is not configured: {error.model}",
            ) from error
        except ProviderError as error:
            # TODO(applied-ai-exercise): This intentionally coarse policy hides
            # useful retryability distinctions such as rate limiting versus a
            # malformed upstream response. Design the policy before refining it.
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The configured AI provider failed.",
            ) from error

        return GenerationResponse(
            text=result.text,
            model=result.model,
            provider=result.provider,
            usage=UsageResponse(
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            ),
        )

    return app
