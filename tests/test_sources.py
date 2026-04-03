import json
from pathlib import Path

import pytest

from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.task_exceptions import TaskIdError
from src.task_platform.task_repr import Task


def _assert_task_shape(tasks: list[Task]) -> None:
    assert tasks
    for task in tasks:
        assert isinstance(task.id, str)


def test_file_source_returns_tasks(tmp_path: Path) -> None:
    file_path = tmp_path / "tasks.json"
    file_path.write_text(
        json.dumps(
            [
                {"id": "f-1", "payload": {"a": 1}},
                {"id": "f-2", "payload": {"a": 2}},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    tasks = FileTaskSource(file_path).get_tasks()

    _assert_task_shape(tasks)
    assert [task.id for task in tasks] == ["f-1", "f-2"]


def test_generator_source_returns_tasks() -> None:
    tasks = GeneratorTaskSource(count=3, prefix="g").get_tasks()

    _assert_task_shape(tasks)
    assert [task.id for task in tasks] == ["g-0", "g-1", "g-2"]


def test_api_stub_source_returns_tasks() -> None:
    expected = [Task(id="api-1", payload={"status": "new"})]

    tasks = ApiStubTaskSource(expected).get_tasks()

    _assert_task_shape(tasks)
    assert tasks == expected


def test_payload_can_be_non_dict() -> None:
    expected = [Task(id="api-raw", payload="text payload")]

    tasks = ApiStubTaskSource(expected).get_tasks()

    _assert_task_shape(tasks)
    assert tasks == expected


def test_intake_many_collects_from_all_sources(tmp_path: Path) -> None:
    file_path = tmp_path / "tasks.json"
    file_path.write_text(
        json.dumps([{"id": "f-1", "payload": {"source": "file"}}], ensure_ascii=False),
        encoding="utf-8",
    )

    tasks = intake_many(
        [
            FileTaskSource(file_path),
            GeneratorTaskSource(count=1, prefix="gen"),
            ApiStubTaskSource([Task(id="api-1", payload={"source": "api"})]),
        ]
    )

    _assert_task_shape(tasks)
    assert [task.id for task in tasks] == ["f-1", "gen-0", "api-1"]


def test_file_source_requires_json_list(tmp_path: Path) -> None:
    file_path = tmp_path / "tasks.json"
    file_path.write_text(
        json.dumps({"id": "f-1", "payload": {"source": "file"}}, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="список задач"):
        FileTaskSource(file_path).get_tasks()


def test_file_source_requires_object_items(tmp_path: Path) -> None:
    file_path = tmp_path / "tasks.json"
    file_path.write_text(json.dumps(["broken"], ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="индексу 0"):
        FileTaskSource(file_path).get_tasks()


def test_file_source_preserves_task_id_validation(tmp_path: Path) -> None:
    file_path = tmp_path / "tasks.json"
    file_path.write_text(
        json.dumps([{"id": 123, "payload": {"source": "file"}}], ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(TaskIdError, match="ожидается строка"):
        FileTaskSource(file_path).get_tasks()
