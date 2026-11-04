"""Domain exceptions for text ingestion and processing."""

from __future__ import annotations

from typing import Any, Mapping


class ProcessingError(Exception):
    """Base exception carrying structured, caller-readable context."""

    def __init__(self, message: str, context: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.context = dict(context or {})


class DataValidationError(ProcessingError, ValueError):
    """Raised when input has an invalid type or value."""


class EmptyTokenStreamError(ProcessingError):
    """Raised when an operation requires numeric tokens but none exist."""


class MalformedPayloadException(DataValidationError):
    """Raised when an external or serialized payload is malformed."""


class ArithmeticAggregationError(ProcessingError, ArithmeticError):
    """Raised when numeric aggregation cannot produce finite results."""


class TokenCorruptedError(DataValidationError):
    """Compatibility exception for malformed delimited numeric input."""