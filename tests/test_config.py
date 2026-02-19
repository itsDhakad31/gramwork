"""Tests for config loading."""

import os
import tempfile

import pytest

from gramwork.config import Config, ConfigError, load_config


def test_default_config():
    cfg = load_config()
    assert cfg.telegram.api_id == 0
    assert cfg.telegram.session_name == "gramwork"
    assert cfg.safety.rate_limit_per_chat == 5.0


def test_load_from_toml():
    content = """\
[telegram]
api_id = 12345
api_hash = "abc123"
session_name = "test"

[safety]
rate_limit_per_chat = 10.0

[plugins.autoreply]
system_prompt = "Hello"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(content)
        f.flush()
        cfg = load_config(f.name)

    assert cfg.telegram.api_id == 12345
    assert cfg.telegram.api_hash == "abc123"
    assert cfg.safety.rate_limit_per_chat == 10.0
    assert cfg.plugins["autoreply"]["system_prompt"] == "Hello"
    os.unlink(f.name)


def test_env_override(monkeypatch):
    monkeypatch.setenv("GRAMWORK_API_ID", "99999")
    monkeypatch.setenv("GRAMWORK_API_HASH", "envhash")
    cfg = load_config()
    assert cfg.telegram.api_id == 99999
    assert cfg.telegram.api_hash == "envhash"


def test_missing_file():
    with pytest.raises(ConfigError):
        load_config("/nonexistent/path.toml")
