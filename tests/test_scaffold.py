"""Tests for CLI scaffolding."""

import tempfile
from pathlib import Path

from gramwork.cli.scaffold import scaffold_project


def test_scaffold_creates_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = scaffold_project("myagent", tmpdir)
        assert project_dir == Path(tmpdir) / "myagent"
        assert (project_dir / "pyproject.toml").exists()
        assert (project_dir / "config.toml").exists()
        assert (project_dir / "myagent.py").exists()

        # Check content
        agent_code = (project_dir / "myagent.py").read_text()
        assert "GramWork" in agent_code
        assert "/ping" in agent_code

        config = (project_dir / "config.toml").read_text()
        assert 'session_name = "myagent"' in config
