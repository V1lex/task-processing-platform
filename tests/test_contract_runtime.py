from typing import Any

import pytest

from src.task_platform.intake import InvalidTaskSourceError, intake_tasks
from src.task_platform.protocols import TaskSource
from src.task_platform.task_repr import Task


class ValidSource:
    def get_tasks(self) -> list[Task]:
        return [Task(id="ok", payload={"k": "v"})]


class InvalidSource:
    def get_items(self) -> list[dict[str, Any]]:
        return []


class NonCallableSource:
    get_tasks = []


class WrongResultTypeSource:
    def get_tasks(self) -> tuple[Task, ...]:
        return (Task(id="tuple", payload=None),)


class WrongTaskItemSource:
    def get_tasks(self) -> list[object]:
        return [Task(id="ok", payload=None), {"id": "broken"}]


def test_runtime_protocol_check_with_isinstance() -> None:
    assert isinstance(ValidSource(), TaskSource)
    assert not isinstance(InvalidSource(), TaskSource)


def test_runtime_protocol_check_with_issubclass() -> None:
    assert issubclass(ValidSource, TaskSource)
    assert not issubclass(InvalidSource, TaskSource)


def test_intake_raises_clear_error_for_invalid_contract() -> None:
    with pytest.raises(InvalidTaskSourceError, match="контракт TaskSource"):
        intake_tasks(InvalidSource())


def test_intake_rejects_non_callable_get_tasks() -> None:
    assert isinstance(NonCallableSource(), TaskSource)

    with pytest.raises(InvalidTaskSourceError, match="вызываемый метод"):
        intake_tasks(NonCallableSource())


def test_intake_rejects_non_list_result() -> None:
    with pytest.raises(InvalidTaskSourceError, match="список"):
        intake_tasks(WrongResultTypeSource())


def test_intake_rejects_non_task_items() -> None:
    with pytest.raises(InvalidTaskSourceError, match="не является Task"):
        intake_tasks(WrongTaskItemSource())
