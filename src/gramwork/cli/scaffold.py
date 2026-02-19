"""Project scaffolding — `gramwork new` command."""

from __future__ import annotations

from pathlib import Path

_PYPROJECT_TEMPLATE = '''\
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "gramwork",
]

[project.scripts]
{name} = "{name_under}:main"
'''

_CONFIG_TEMPLATE = """\
[telegram]
api_id = 0
api_hash = ""
session_name = "{name}"
# phone = "+1234567890"

[safety]
rate_limit_per_chat = 5.0
rate_limit_global = 30.0
rate_limit_burst = 10

# [plugins.autoreply]
# system_prompt = "You are a helpful assistant."
"""

_AGENT_TEMPLATE = '''\
"""Minimal {name} agent."""

from gramwork import GramWork

app = GramWork(config_path="config.toml")


@app.on_message(pattern=r"/ping")
async def ping(ctx):
    await ctx.reply("pong!")


def main():
    app.run()


if __name__ == "__main__":
    main()
'''


def scaffold_project(name: str, parent: str = ".") -> Path:
    """Create a project directory with boilerplate files."""
    name_under = name.replace("-", "_")
    project_dir = Path(parent) / name
    project_dir.mkdir(parents=True, exist_ok=True)

    (project_dir / "pyproject.toml").write_text(
        _PYPROJECT_TEMPLATE.format(name=name, name_under=name_under)
    )
    (project_dir / "config.toml").write_text(
        _CONFIG_TEMPLATE.format(name=name)
    )
    (project_dir / f"{name_under}.py").write_text(
        _AGENT_TEMPLATE.format(name=name)
    )

    return project_dir
