import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.task_exceptions import (
    TaskCreatedAtError,
    TaskDescriptionError,
    TaskIdError,
    TaskImmutableFieldError,
    TaskPriorityError,
    TaskStateTransitionError,
    TaskStatusError,
)
from src.task_platform.task_repr import Task


def test_task_initializes_with_safe_defaults() -> None:
    task = Task(id=" task-1 ", payload={"kind": "sync"})

    assert task.id == "task-1"
    assert task.description == "Задача task-1"
    assert task.priority == 3
    assert task.status == "pending"
    assert task.is_ready is True
    assert task.is_terminal is False
    assert task.created_at.tzinfo == timezone.utc


def test_task_normalizes_timestamp_and_status_aliases() -> None:
    created_at = datetime(2026, 4, 2, 9, 30, 0)

    task = Task(
        id="task-2",
        payload=None,
        description="Закрыть спринт",
        status="done",
        created_at=created_at,
    )

    assert task.status == "completed"
    assert task.created_at == created_at.replace(tzinfo=timezone.utc)
    assert task.is_terminal is True


def test_task_rejects_invalid_attribute_values() -> None:
    with pytest.raises(TaskIdError):
        Task(id=" ", payload=None)

    with pytest.raises(TaskDescriptionError):
        Task(id="task-3", payload=None, description="  ")

    with pytest.raises(TaskPriorityError):
        Task(id="task-4", payload=None, priority=0)

    with pytest.raises(TaskStatusError):
        Task(id="task-5", payload=None, status="archived")

    with pytest.raises(TaskCreatedAtError):
        Task(id="task-6", payload=None, created_at="2026-04-02T09:30:00Z")


def test_write_once_fields_cannot_be_reassigned() -> None:
    task = Task(id="task-7", payload=None)

    with pytest.raises(TaskImmutableFieldError, match="id"):
        task.id = "task-7-updated"

    with pytest.raises(TaskImmutableFieldError, match="created_at"):
        task.created_at = datetime.now(timezone.utc)


def test_status_transitions_are_validated() -> None:
    task = Task(id="task-8", payload=None)

    with pytest.raises(TaskStateTransitionError):
        task.status = "completed"

    task.status = "in_progress"
    assert task.is_ready is False

    task.status = "done"
    assert task.status == "completed"
    assert task.is_terminal is True

    with pytest.raises(TaskStateTransitionError):
        task.status = "pending"


def test_task_blocks_unknown_public_attributes() -> None:
    task = Task(id="task-9", payload=None)

    with pytest.raises(AttributeError, match="не имеет публичного атрибута"):
        task.owner = "backend-team"


def test_data_descriptor_has_priority_over_instance_dict() -> None:
    task = Task(id="task-10", payload=None)
    task.__dict__["priority"] = 1

    assert task.priority == 3


def test_non_data_descriptor_can_be_shadowed_by_instance_attribute() -> None:
    task = Task(id="task-11", payload=None, description="Подготовить отчёт")

    assert task.summary == "task-11 [pending, p3] Подготовить отчёт"

    task.summary = "ручное краткое описание"
    assert task.summary == "ручное краткое описание"

    del task.__dict__["summary"]
    assert task.summary == "task-11 [pending, p3] Подготовить отчёт"


def test_file_source_supports_extended_task_model(tmp_path: Path) -> None:
    file_path = tmp_path / "tasks.json"
    file_path.write_text(
        json.dumps(
            [
                {
                    "id": "file-1",
                    "payload": {"kind": "email"},
                    "description": "Отправить приветственное письмо",
                    "priority": 5,
                    "status": "new",
                    "created_at": "2026-04-02T09:30:00+00:00",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    task = FileTaskSource(file_path).get_tasks()[0]

    assert task.description == "Отправить приветственное письмо"
    assert task.priority == 5
    assert task.status == "pending"
    assert task.created_at == datetime(2026, 4, 2, 9, 30, tzinfo=timezone.utc)
