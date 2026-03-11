from __future__ import annotations

import json
from pathlib import Path

from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
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
