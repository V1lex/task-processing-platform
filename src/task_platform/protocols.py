from typing import Protocol, runtime_checkable

from src.task_platform.task_repr import Task


@runtime_checkable
class TaskSource(Protocol):
    """Контракт для любого источника, который может выдавать задачи."""

    def get_tasks(self) -> list[Task]:
        """Возвращает задачи из текущего источника."""


@runtime_checkable
class AsyncTaskHandler(Protocol):
    """Контракт асинхронного обработчика задач."""

    def can_handle(self, task: Task) -> bool:
        """Показывает, может ли обработчик выполнить задачу."""

    async def handle(self, task: Task) -> None:
        """Асинхронно выполняет прикладную логику задачи."""
