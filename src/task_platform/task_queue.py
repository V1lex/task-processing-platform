from collections.abc import Iterable, Iterator

from src.task_platform.task_descriptors import TaskStatusDescriptor
from src.task_platform.task_exceptions import TaskPriorityError, TaskStatusError
from src.task_platform.task_repr import Task


class TaskQueueIterator:
    """Итератор по очереди задач."""

    def __init__(self, tasks: list[Task]) -> None:
        self._tasks = tasks
        self._index = 0

    def __iter__(self) -> "TaskQueueIterator":
        return self

    def __next__(self) -> Task:
        if self._index >= len(self._tasks):
            raise StopIteration

        task = self._tasks[self._index]
        self._index += 1
        return task


class TaskQueue:
    """Повторяемая коллекция задач с ленивыми фильтрами."""

    def __init__(self, tasks: Iterable[Task] = ()) -> None:
        self._tasks: list[Task] = []
        self.extend(tasks)

    def __iter__(self) -> TaskQueueIterator:
        return TaskQueueIterator(self._tasks)

    def __len__(self) -> int:
        return len(self._tasks)

    def __repr__(self) -> str:
        return f"TaskQueue(size={len(self._tasks)})"

    def add(self, task: Task) -> None:
        """Добавляет одну задачу в очередь."""
        self._tasks.append(self._ensure_task(task))

    def extend(self, tasks: Iterable[Task]) -> None:
        """Добавляет в очередь последовательность задач."""
        for task in tasks:
            self.add(task)

    def filter_by_status(self, status: str) -> Iterator[Task]:
        """Лениво возвращает задачи с указанным статусом."""
        normalized_status = self._normalize_status(status)
        return (task for task in self if task.status == normalized_status)

    def filter_by_priority(self, minimum_priority: int) -> Iterator[Task]:
        """Лениво возвращает задачи с приоритетом не ниже указанного."""
        normalized_priority = self._normalize_priority(minimum_priority)
        return (task for task in self if task.priority >= normalized_priority)

    def _ensure_task(self, task: Task) -> Task:
        if not isinstance(task, Task):
            raise TypeError("Очередь задач принимает только экземпляры Task")
        return task

    def _normalize_status(self, status: str) -> str:
        if not isinstance(status, str):
            raise TaskStatusError("ожидается строка")

        normalized_status = status.strip().lower()
        if not normalized_status:
            raise TaskStatusError("статус не может быть пустым")

        normalized_status = TaskStatusDescriptor.aliases.get(
            normalized_status,
            normalized_status,
        )
        if normalized_status not in TaskStatusDescriptor.allowed_statuses:
            allowed_values = ", ".join(sorted(TaskStatusDescriptor.allowed_statuses))
            raise TaskStatusError(
                f"неподдерживаемый статус {normalized_status!r}; допустимые значения: {allowed_values}"
            )

        return normalized_status

    def _normalize_priority(self, priority: int) -> int:
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise TaskPriorityError("ожидается целое число от 1 до 5")

        if priority < 1 or priority > 5:
            raise TaskPriorityError("приоритет должен быть в диапазоне от 1 до 5")

        return priority
