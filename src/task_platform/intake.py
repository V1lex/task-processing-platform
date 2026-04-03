from collections.abc import Iterable

from src.task_platform.protocols import TaskSource
from src.task_platform.task_repr import Task


class InvalidTaskSourceError(TypeError):
    """Выбрасывается, когда объект не удовлетворяет контракту TaskSource."""


def _validate_loaded_tasks(tasks: object) -> list[Task]:
    if not isinstance(tasks, list):
        raise InvalidTaskSourceError(
            "Источник вернул некорректный результат: ожидается список list[Task]"
        )

    for index, task in enumerate(tasks):
        if not isinstance(task, Task):
            raise InvalidTaskSourceError(
                "Источник вернул некорректный результат: "
                f"элемент с индексом {index} не является Task"
            )

    return tasks


def intake_tasks(source: TaskSource) -> list[Task]:
    """Собирает задачи из одного источника с runtime-проверкой контракта."""
    get_tasks = getattr(source, "get_tasks", None)
    if not isinstance(source, TaskSource) or not callable(get_tasks):
        raise InvalidTaskSourceError(
            "Источник не реализует контракт TaskSource: "
            "ожидается вызываемый метод get_tasks() -> list[Task]"
        )

    return _validate_loaded_tasks(get_tasks())


def intake_many(sources: Iterable[TaskSource]) -> list[Task]:
    """Собирает задачи из нескольких источников через единый контракт."""
    tasks: list[Task] = []
    for source in sources:
        tasks.extend(intake_tasks(source))
    return tasks
