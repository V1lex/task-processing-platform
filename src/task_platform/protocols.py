from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.task_platform.task_repr import Task


@runtime_checkable
class TaskSource(Protocol):
    """Контракт для любого источника, который может выдавать задачи."""

    def get_tasks(self) -> list[Task]:
        """Возвращает задачи из текущего источника."""
