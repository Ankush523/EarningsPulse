"""API exception handlers and error schemas."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.errors import ConfigurationError, DataNotFoundError, ServiceError
from app.services.job_store import JobNotFoundError


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(JobNotFoundError)
    async def job_not_found_handler(_: Request, exc: JobNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                detail=f"Job not found: {exc.args[0]}",
                error_code="job_not_found",
            ).model_dump(),
        )

    @app.exception_handler(DataNotFoundError)
    async def data_not_found_handler(_: Request, exc: DataNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                detail=str(exc),
                error_code="data_not_found",
            ).model_dump(),
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(_: Request, exc: ConfigurationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                detail=str(exc),
                error_code="configuration_error",
            ).model_dump(),
        )

    @app.exception_handler(ServiceError)
    async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        code = status.HTTP_502_BAD_GATEWAY if exc.retryable else status.HTTP_400_BAD_REQUEST
        return JSONResponse(
            status_code=code,
            content=ErrorResponse(
                detail=str(exc),
                error_code="service_error",
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                detail="Request validation failed",
                error_code="validation_error",
            ).model_dump()
            | {"errors": exc.errors()},
        )
