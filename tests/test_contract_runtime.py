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


def test_runtime_protocol_check_with_isinstance() -> None:
    assert isinstance(ValidSource(), TaskSource)
    assert not isinstance(InvalidSource(), TaskSource)


def test_runtime_protocol_check_with_issubclass() -> None:
    assert issubclass(ValidSource, TaskSource)
    assert not issubclass(InvalidSource, TaskSource)


def test_intake_raises_clear_error_for_invalid_contract() -> None:
    with pytest.raises(InvalidTaskSourceError, match="контракт TaskSource"):
        intake_tasks(InvalidSource())
