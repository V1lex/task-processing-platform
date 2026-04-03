import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.task_platform.task_repr import Task


class FileTaskSource:
    """Источник задач, загружающий их из JSON-файла."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def get_tasks(self) -> list[Task]:
        """Считывает и парсит задачи из JSON-файла."""
        raw_items = json.loads(self._file_path.read_text(encoding="utf-8"))
        if not isinstance(raw_items, list):
            raise ValueError("JSON-файл должен содержать список задач")

        return [self._build_task(item, index) for index, item in enumerate(raw_items)]

    def _build_task(self, item: Any, index: int) -> Task:
        if not isinstance(item, dict):
            raise ValueError(
                "Каждая задача в JSON-файле должна быть объектом; "
                f"некорректный элемент найден по индексу {index}"
            )

        created_at = self._parse_created_at(item.get("created_at"))
        return Task(
            id=item["id"],
            payload=item["payload"],
            description=item.get("description"),
            priority=item.get("priority", 3),
            status=item.get("status", "pending"),
            created_at=created_at,
        )

    def _parse_created_at(self, raw_value: Any) -> datetime | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, datetime):
            return raw_value
        if isinstance(raw_value, str):
            return datetime.fromisoformat(raw_value)
        return raw_value
