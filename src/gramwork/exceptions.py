"""gramwork exceptions."""


class GramWorkError(Exception):
    """Base exception for gramwork."""


class ConfigError(GramWorkError):
    """Invalid or missing configuration."""


class StopPropagation(GramWorkError):
    """Stops the middleware/handler chain."""


class LLMError(GramWorkError):
    """LLM call failed."""


class StateError(GramWorkError):
    """State backend operation failed."""


class PluginError(GramWorkError):
    """Plugin loading or configuration failed."""


class SecurityError(GramWorkError):
    """Vault or encryption operation failed."""


class ToolError(GramWorkError):
    """Tool execution failed."""


class AutonomousError(GramWorkError):
    """Autonomous brain error."""
