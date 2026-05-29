
class SkillEvalException(Exception):
    """Base exception for skill evaluation errors."""
    pass


class ProviderError(SkillEvalException):
    """Raised when a provider fails to return a valid response."""
    pass


class ValidationError(SkillEvalException):
    """Raised when a result fails schema validation."""
    pass
