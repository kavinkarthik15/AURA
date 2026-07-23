class ModelNotFoundError(FileNotFoundError):
    """Raised when a learned model artifact is required but is not present."""

    pass
