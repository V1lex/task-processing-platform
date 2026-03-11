from __future__ import annotations

from src.task_platform.protocols import TaskSource
from src.task_platform.task_repr import Task


class InvalidTaskSourceError(TypeError):
    """Выбрасывается, когда объект не удовлетворяет контракту TaskSource."""


def intake_tasks(source: TaskSource) -> list[Task]:
    """Собирает задачи из одного источника с runtime-проверкой контракта."""
    if not isinstance(source, TaskSource):
        raise InvalidTaskSourceError(
            "Источник не реализует контракт TaskSource: ожидается метод get_tasks() -> list[Task]"
        )
    return source.get_tasks()


def intake_many(sources: list[TaskSource]) -> list[Task]:
    """Собирает задачи из нескольких источников через единый контракт."""
    tasks: list[Task] = []
    for source in sources:
        tasks.extend(intake_tasks(source))
    return tasks
