from __future__ import annotations

from pathlib import Path
import json

from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.task_repr import Task


def main() -> None:
    """Демонстрационный вход в программу для приёма задач из ЛР1."""
    demo_file = Path("demo_tasks.json")
    demo_file.write_text(
        json.dumps(
            [
                {"id": "file-1", "payload": {"source": "file", "value": 10}},
                {"id": "file-2", "payload": {"source": "file", "value": 20}},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    sources = [
        FileTaskSource(demo_file),
        GeneratorTaskSource(count=2, prefix="gen"),
        ApiStubTaskSource([Task(id="api-1", payload={"source": "api"})]),
    ]

    tasks = intake_many(sources)
    for task in tasks:
        print(f"{task.id}: {task.payload}")


if __name__ == "__main__":
    main()
