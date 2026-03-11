from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Task:
    """Минимальное представление задачи для платформы."""

    id: str
    payload: Any
