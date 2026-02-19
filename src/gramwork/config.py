"""Layered configuration: defaults < TOML file < env vars."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gramwork.exceptions import ConfigError


@dataclass(slots=True)
class TelegramConfig:
    api_id: int = 0
    api_hash: str = ""
    session_name: str = "gramwork"
    phone: str = ""


@dataclass(slots=True)
class SafetyConfig:
    rate_limit_per_chat: float = 5.0
    rate_limit_global: float = 30.0
    rate_limit_burst: int = 10


@dataclass(slots=True)
class LLMConfig:
    provider: str = "ollama"  # "ollama" | "openai_compat"
    model: str = "llama3.1"
    base_url: str = "http://localhost:11434"
    api_key: str = ""  # supports "vault:key_name"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 120.0


@dataclass(slots=True)
class AgentConfig:
    autonomous: bool = False
    system_prompt: str = "You are an autonomous Telegram agent."
    system_prompt_file: str = ""
    tools: list[str] | None = None  # None = all tools
    max_iterations: int = 20
    loop_interval: float = 30.0
    outbound_rate: float = 1.0
    outbound_burst: int = 5


@dataclass(slots=True)
class SecurityConfig:
    vault_path: str = ".gramwork_vault"
    encrypted_session: bool = False
    session_path: str = ".gramwork_session.enc"


@dataclass(slots=True)
class Config:
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    plugins: dict[str, dict[str, Any]] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


def _apply_env(cfg: Config) -> None:
    env_map: dict[str, tuple[object, str]] = {
        "GRAMWORK_API_ID": (cfg.telegram, "api_id"),
        "GRAMWORK_API_HASH": (cfg.telegram, "api_hash"),
        "GRAMWORK_SESSION_NAME": (cfg.telegram, "session_name"),
        "GRAMWORK_PHONE": (cfg.telegram, "phone"),
        "GRAMWORK_RATE_LIMIT_PER_CHAT": (cfg.safety, "rate_limit_per_chat"),
        "GRAMWORK_RATE_LIMIT_GLOBAL": (cfg.safety, "rate_limit_global"),
        "GRAMWORK_RATE_LIMIT_BURST": (cfg.safety, "rate_limit_burst"),
        "GRAMWORK_LLM_PROVIDER": (cfg.llm, "provider"),
        "GRAMWORK_LLM_MODEL": (cfg.llm, "model"),
        "GRAMWORK_LLM_BASE_URL": (cfg.llm, "base_url"),
        "GRAMWORK_LLM_API_KEY": (cfg.llm, "api_key"),
        "GRAMWORK_LLM_TEMPERATURE": (cfg.llm, "temperature"),
        "GRAMWORK_LLM_MAX_TOKENS": (cfg.llm, "max_tokens"),
        "GRAMWORK_LLM_TIMEOUT": (cfg.llm, "timeout"),
        "GRAMWORK_AUTONOMOUS": (cfg.agent, "autonomous"),
        "GRAMWORK_SYSTEM_PROMPT": (cfg.agent, "system_prompt"),
        "GRAMWORK_MAX_ITERATIONS": (cfg.agent, "max_iterations"),
        "GRAMWORK_LOOP_INTERVAL": (cfg.agent, "loop_interval"),
        "GRAMWORK_OUTBOUND_RATE": (cfg.agent, "outbound_rate"),
        "GRAMWORK_OUTBOUND_BURST": (cfg.agent, "outbound_burst"),
        "GRAMWORK_VAULT_PATH": (cfg.security, "vault_path"),
        "GRAMWORK_ENCRYPTED_SESSION": (cfg.security, "encrypted_session"),
        "GRAMWORK_SESSION_PATH": (cfg.security, "session_path"),
    }
    for env_key, (obj, attr) in env_map.items():
        val = os.environ.get(env_key)
        if val is None:
            continue
        current = getattr(obj, attr)
        if isinstance(current, bool):
            setattr(obj, attr, val.lower() in ("1", "true", "yes"))
        elif isinstance(current, int):
            setattr(obj, attr, int(val))
        elif isinstance(current, float):
            setattr(obj, attr, float(val))
        else:
            setattr(obj, attr, val)


def _apply_section(obj: object, data: dict[str, Any]) -> None:
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)


def _resolve_vault_refs(cfg: Config, vault: Any) -> None:
    """Replace ``vault:key_name`` strings with actual vault values."""
    for obj in (cfg.telegram, cfg.llm):
        for attr in obj.__slots__:
            val = getattr(obj, attr)
            if isinstance(val, str) and val.startswith("vault:"):
                key_name = val[len("vault:"):]
                resolved = vault.get(key_name)
                if attr == "api_id":
                    resolved = int(resolved)
                setattr(obj, attr, resolved)


def load_config(path: str | Path | None = None) -> Config:
    cfg = Config()

    if path is not None:
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"Config file not found: {p}")
        with open(p, "rb") as f:
            data = tomllib.load(f)

        if "telegram" in data:
            _apply_section(cfg.telegram, data["telegram"])
        if "safety" in data:
            _apply_section(cfg.safety, data["safety"])
        if "llm" in data:
            _apply_section(cfg.llm, data["llm"])
        if "agent" in data:
            _apply_section(cfg.agent, data["agent"])
        if "security" in data:
            _apply_section(cfg.security, data["security"])

        cfg.plugins = data.get("plugins", {})

        known = {"telegram", "safety", "llm", "agent", "security", "plugins"}
        for key in data:
            if key not in known:
                cfg.extra[key] = data[key]

    _apply_env(cfg)
    return cfg
