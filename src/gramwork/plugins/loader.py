"""Plugin discovery via entry points."""

from __future__ import annotations

import importlib.metadata
import logging
from typing import Any

from gramwork.exceptions import PluginError

logger = logging.getLogger("gramwork.plugins")

ENTRY_POINT_GROUP = "gramwork.plugins"


def discover_plugins() -> list[Any]:
    """Discover and instantiate plugins from installed entry points."""
    plugins: list[Any] = []
    eps = importlib.metadata.entry_points()

    # Python 3.12+ returns a SelectableGroups, 3.9+ dict-like
    if hasattr(eps, "select"):
        group_eps = eps.select(group=ENTRY_POINT_GROUP)
    else:
        group_eps = eps.get(ENTRY_POINT_GROUP, [])  # type: ignore[assignment]

    for ep in group_eps:
        try:
            plugin_cls = ep.load()
            plugin = plugin_cls()
            plugins.append(plugin)
            logger.info("Discovered plugin: %s", ep.name)
        except Exception as exc:
            raise PluginError(f"Failed to load plugin '{ep.name}': {exc}") from exc

    return plugins
