"""Expected business errors translated by API adapters."""


class BusinessError(ValueError):
    """Base class for expected domain failures."""


class DuplicateResourceError(BusinessError):
    """A unique business identifier is already in use."""


class ResourceNotFoundError(BusinessError):
    """A referenced business resource does not exist."""


class InsufficientStockError(BusinessError):
    """A sale requested more stock than is available."""


class IdempotencyConflictError(BusinessError):
    """A key was reused with a different command payload."""
