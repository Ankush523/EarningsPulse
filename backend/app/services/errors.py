"""Service-layer exceptions."""


class ServiceError(Exception):
    """Base exception for external service failures."""

    def __init__(self, message: str, *, service: str, retryable: bool = False):
        self.service = service
        self.retryable = retryable
        super().__init__(message)


class ConfigurationError(ServiceError):
    """Raised when required configuration is missing."""

    def __init__(self, message: str, *, service: str):
        super().__init__(message, service=service, retryable=False)


class DataNotFoundError(ServiceError):
    """Raised when requested data does not exist."""

    def __init__(self, message: str, *, service: str):
        super().__init__(message, service=service, retryable=False)


class RateLimitError(ServiceError):
    """Raised when an external API rate limit is hit."""

    def __init__(self, message: str, *, service: str):
        super().__init__(message, service=service, retryable=True)
