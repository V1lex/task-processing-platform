import inspect

import pytest

from src.task_platform.task_exceptions import TaskPriorityError, TaskStatusError
from src.task_platform.task_queue import TaskQueue, TaskQueueIterator
from src.task_platform.task_repr import Task


def _build_tasks() -> list[Task]:
    return [
        Task(
            id="task-1",
            payload={"kind": "email"},
            description="Отправить письмо",
            priority=5,
            status="new",
        ),
        Task(
            id="task-2",
            payload={"kind": "report"},
            description="Подготовить отчёт",
            priority=3,
            status="in_progress",
        ),
        Task(
            id="task-3",
            payload={"kind": "sync"},
            description="Синхронизировать CRM",
            priority=4,
            status="pending",
        ),
    ]


def test_task_queue_supports_repeated_iteration() -> None:
    queue = TaskQueue(_build_tasks())

    first_pass = [task.id for task in queue]
    second_pass = [task.id for task in queue]

    assert first_pass == ["task-1", "task-2", "task-3"]
    assert second_pass == first_pass


def test_task_queue_returns_custom_iterator_and_handles_stop_iteration() -> None:
    queue = TaskQueue(_build_tasks())

    iterator = iter(queue)

    assert isinstance(iterator, TaskQueueIterator)
    assert next(iterator).id == "task-1"
    assert next(iterator).id == "task-2"
    assert next(iterator).id == "task-3"

    with pytest.raises(StopIteration):
        next(iterator)


def test_status_filter_is_lazy_and_normalizes_aliases() -> None:
    queue = TaskQueue(_build_tasks())
    filtered_tasks = queue.filter_by_status("new")

    assert inspect.isgenerator(filtered_tasks)

    queue.add(
        Task(
            id="task-4",
            payload={"kind": "notification"},
            description="Отправить уведомление",
            priority=2,
            status="pending",
        )
    )

    assert [task.id for task in filtered_tasks] == ["task-1", "task-3", "task-4"]


def test_priority_filter_is_lazy_and_compatible_with_standard_constructs() -> None:
    queue = TaskQueue(_build_tasks())
    high_priority_tasks = queue.filter_by_priority(4)

    assert inspect.isgenerator(high_priority_tasks)
    assert [task.id for task in high_priority_tasks] == ["task-1", "task-3"]
    assert list(queue)
    assert sum(task.priority for task in queue) == 12


def test_task_queue_validates_filter_arguments() -> None:
    queue = TaskQueue(_build_tasks())

    with pytest.raises(TaskStatusError):
        list(queue.filter_by_status("archived"))

    with pytest.raises(TaskPriorityError):
        list(queue.filter_by_priority(0))


def test_task_queue_accepts_only_task_instances() -> None:
    queue = TaskQueue()

    with pytest.raises(TypeError, match="только экземпляры Task"):
        queue.add("не задача")
