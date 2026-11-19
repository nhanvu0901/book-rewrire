"""Atomic JSON writes for a run's output files."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def save_json(path: Path, value: Any) -> None:
    _write_atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def save_model(path: Path, model: BaseModel) -> None:
    _write_atomic(path, model.model_dump_json(indent=2) + "\n")
