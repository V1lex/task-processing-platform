from collections.abc import Iterator

from src.task_platform.task_repr import Task


class GeneratorTaskSource:
    """Источник задач, генерирующий их программно."""

    def __init__(self, count: int, prefix: str = "generated") -> None:
        self._count = count
        self._prefix = prefix

    def _iter_tasks(self) -> Iterator[Task]:
        for index in range(self._count):
            yield Task(id=f"{self._prefix}-{index}", payload={"index": index})

    def get_tasks(self) -> list[Task]:
        """Возвращает сгенерированные задачи в виде списка."""
        return list(self._iter_tasks())
