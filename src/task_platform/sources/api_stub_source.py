from src.task_platform.task_repr import Task


class ApiStubTaskSource:
    """Источник задач, имитирующий ответ удалённого API."""

    def __init__(self, tasks: list[Task]) -> None:
        self._tasks = list(tasks)

    def get_tasks(self) -> list[Task]:
        """Возвращает задачи, полученные от API-заглушки."""
        return list(self._tasks)
