"""Shared exception types."""


class ModelNotReadyError(RuntimeError):
    """Raised when a trained model or index is missing or cannot be loaded."""
