"""Logging setup for gramwork."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


def setup_logging(level: int | str = logging.INFO) -> None:
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger("gramwork")
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
    root_logger.propagate = False


class JsonFormatter(logging.Formatter):
    """Single-line JSON formatter for JSONL audit logs."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for attr in ("tool_name", "tool_args", "tool_result",
                      "duration_ms", "is_error"):
            if hasattr(record, attr):
                entry[attr] = getattr(record, attr)
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])
        return json.dumps(entry, default=str)


def setup_audit_logging(path: str) -> logging.Logger:
    """Set up gramwork.audit logger writing JSONL to *path*."""
    audit_logger = logging.getLogger("gramwork.audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False

    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    audit_logger.addHandler(handler)
    return audit_logger
