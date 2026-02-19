"""Click CLI for gramwork."""

from __future__ import annotations

import os

import click

from gramwork._version import __version__


@click.group()
@click.version_option(__version__, prog_name="gramwork")
def cli() -> None:
    """gramwork — Telegram user-agent framework for AI agents."""


@cli.command()
@click.argument("name")
@click.option("--directory", "-d", default=".", help="Parent directory.")
def new(name: str, directory: str) -> None:
    """Scaffold a new gramwork project."""
    from gramwork.cli.scaffold import scaffold_project

    scaffold_project(name, directory)
    click.echo(f"Created project '{name}' in {directory}/{name}")


@cli.command()
@click.option("--config", "-c", default="config.toml", help="Config file path.")
def run(config: str) -> None:
    """Run a gramwork agent from config."""
    from gramwork.app import GramWork
    from gramwork.config import _resolve_vault_refs, load_config
    from gramwork.logging import setup_audit_logging, setup_logging
    from gramwork.plugins.loader import discover_plugins

    setup_logging()
    cfg = load_config(config)

    vault = _maybe_unlock_vault(cfg)
    if vault is not None:
        _resolve_vault_refs(cfg, vault)

    llm = _build_llm_provider(cfg.llm)

    session = None
    if cfg.security.encrypted_session:
        session = _load_session(cfg.security, vault)

    setup_audit_logging("gramwork_audit.jsonl")
    app = GramWork(config=cfg, llm=llm, session=session)

    for plugin in discover_plugins():
        app.register_plugin(plugin)

    app.run()


@cli.command(name="plugins")
def list_plugins() -> None:
    """List discovered gramwork plugins."""
    from gramwork.plugins.loader import discover_plugins

    plugins = discover_plugins()
    if not plugins:
        click.echo("No plugins discovered.")
        return
    for p in plugins:
        name = getattr(p, "name", p.__class__.__name__)
        click.echo(f"  - {name}")


@cli.group()
def vault() -> None:
    """Manage the encrypted secret vault."""


@vault.command(name="init")
@click.option("--path", default=".gramwork_vault", help="Vault file path.")
def vault_init(path: str) -> None:
    """Create a new encrypted vault."""
    from gramwork.security.vault import Vault

    password = click.prompt(
        "Master password", hide_input=True, confirmation_prompt=True
    )
    v = Vault(path)
    v.init(password)
    click.echo(f"Vault created at {path}")


@vault.command(name="set")
@click.argument("key")
@click.argument("value")
@click.option("--path", default=".gramwork_vault", help="Vault file path.")
def vault_set(key: str, value: str, path: str) -> None:
    """Store a secret in the vault."""
    from gramwork.security.vault import Vault

    password = _get_master_password()
    v = Vault(path)
    v.unlock(password)
    v.set(key, value, password)
    click.echo(f"Stored '{key}'")


@vault.command(name="get")
@click.argument("key")
@click.option("--path", default=".gramwork_vault", help="Vault file path.")
def vault_get(key: str, path: str) -> None:
    """Retrieve a secret from the vault."""
    from gramwork.security.vault import Vault

    password = _get_master_password()
    v = Vault(path)
    v.unlock(password)
    click.echo(v.get(key))


@vault.command(name="list")
@click.option("--path", default=".gramwork_vault", help="Vault file path.")
def vault_list(path: str) -> None:
    """List all keys in the vault."""
    from gramwork.security.vault import Vault

    password = _get_master_password()
    v = Vault(path)
    v.unlock(password)
    keys = v.list_keys()
    if not keys:
        click.echo("Vault is empty.")
        return
    for k in keys:
        click.echo(f"  - {k}")


def _get_master_password() -> str:
    password = os.environ.get("GRAMWORK_MASTER_PASSWORD")
    if password:
        return password
    return click.prompt("Master password", hide_input=True)


def _maybe_unlock_vault(cfg: object) -> object | None:
    from gramwork.config import Config

    assert isinstance(cfg, Config)

    needs_vault = False
    for obj in [cfg.telegram, cfg.llm]:
        for attr in obj.__slots__:
            val = getattr(obj, attr)
            if isinstance(val, str) and val.startswith("vault:"):
                needs_vault = True
                break

    if not needs_vault:
        return None

    from gramwork.security.vault import Vault

    v = Vault(cfg.security.vault_path)
    password = _get_master_password()
    v.unlock(password)
    return v


def _build_llm_provider(llm_cfg: object) -> object | None:
    from gramwork.config import LLMConfig

    assert isinstance(llm_cfg, LLMConfig)

    if llm_cfg.provider == "ollama":
        from gramwork.llm.ollama import OllamaConfig, OllamaProvider

        return OllamaProvider(OllamaConfig(
            base_url=llm_cfg.base_url,
            model=llm_cfg.model,
            temperature=llm_cfg.temperature,
            timeout=llm_cfg.timeout,
        ))
    elif llm_cfg.provider == "openai_compat":
        from gramwork.llm.openai_compat import (
            OpenAICompatConfig,
            OpenAICompatProvider,
        )

        return OpenAICompatProvider(OpenAICompatConfig(
            base_url=llm_cfg.base_url,
            api_key=llm_cfg.api_key,
            model=llm_cfg.model,
            temperature=llm_cfg.temperature,
            max_tokens=llm_cfg.max_tokens,
        ))
    else:
        click.echo(f"Unknown LLM provider: {llm_cfg.provider}", err=True)
        return None


def _load_session(security_cfg: object, vault: object | None) -> object | None:
    from gramwork.config import SecurityConfig
    from gramwork.security.session import load_encrypted_session

    assert isinstance(security_cfg, SecurityConfig)
    password = _get_master_password()
    return load_encrypted_session(security_cfg.session_path, password)


def main() -> None:
    cli()
