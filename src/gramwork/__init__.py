"""gramwork — Telegram user-agent framework for AI agents."""

from gramwork._version import __version__
from gramwork.app import GramWork
from gramwork.config import (
    AgentConfig,
    Config,
    LLMConfig,
    SafetyConfig,
    SecurityConfig,
    TelegramConfig,
    load_config,
)
from gramwork.context import EventContext
from gramwork.exceptions import (
    AutonomousError,
    ConfigError,
    GramWorkError,
    LLMError,
    PluginError,
    SecurityError,
    StateError,
    StopPropagation,
    ToolError,
)
from gramwork.llm import (
    ChatMessage,
    LLMProvider,
    OllamaConfig,
    OllamaProvider,
    OpenAICompatConfig,
    OpenAICompatProvider,
    Role,
    ToolCall,
    ToolResult,
)
from gramwork.middleware import Middleware, MiddlewareStack
from gramwork.plugins import Plugin, discover_plugins
from gramwork.routing import Route, Router
from gramwork.safety import RateLimitMiddleware
from gramwork.security import Vault
from gramwork.state import Conversation, MemoryBackend, StateBackend, Turn
from gramwork.tools import ToolRegistry, ToolSpec

__all__ = [
    "__version__",
    # Core
    "GramWork",
    "EventContext",
    "Router",
    "Route",
    "Middleware",
    "MiddlewareStack",
    # Config
    "Config",
    "TelegramConfig",
    "SafetyConfig",
    "LLMConfig",
    "AgentConfig",
    "SecurityConfig",
    "load_config",
    # LLM
    "LLMProvider",
    "ChatMessage",
    "Role",
    "ToolCall",
    "ToolResult",
    "OllamaProvider",
    "OllamaConfig",
    "OpenAICompatProvider",
    "OpenAICompatConfig",
    # Tools
    "ToolSpec",
    "ToolRegistry",
    # Security
    "Vault",
    # State
    "StateBackend",
    "MemoryBackend",
    "Conversation",
    "Turn",
    # Plugins
    "Plugin",
    "discover_plugins",
    # Safety
    "RateLimitMiddleware",
    # Exceptions
    "GramWorkError",
    "ConfigError",
    "StopPropagation",
    "LLMError",
    "StateError",
    "PluginError",
    "SecurityError",
    "ToolError",
    "AutonomousError",
]
