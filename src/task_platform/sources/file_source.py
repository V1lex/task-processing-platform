from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.task_platform.task_repr import Task


class FileTaskSource:
    """Источник задач, загружающий их из JSON-файла."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def get_tasks(self) -> list[Task]:
        """Считывает и парсит задачи из JSON-файла."""
        raw_items: list[dict[str, Any]] = json.loads(
            self._file_path.read_text(encoding="utf-8")
        )
        return [Task(id=str(item["id"]), payload=item["payload"]) for item in raw_items]
