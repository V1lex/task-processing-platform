from datetime import datetime, timezone

from src.task_platform.task_descriptors import (
    TaskCreatedAtDescriptor,
    TaskDescriptionDescriptor,
    TaskIdDescriptor,
    TaskPriorityDescriptor,
    TaskStatusDescriptor,
    TaskSummaryDescriptor,
)


class Task:
    """Доменная модель задачи с валидацией и защищённым публичным API."""

    id: str = TaskIdDescriptor()
    description: str = TaskDescriptionDescriptor()
    priority: int = TaskPriorityDescriptor()
    status: str = TaskStatusDescriptor()
    created_at: datetime = TaskCreatedAtDescriptor()
    summary = TaskSummaryDescriptor()

    _public_attributes = frozenset(
        {"id", "payload", "description", "priority", "status", "created_at", "summary"}
    )

    def __init__(
        self,
        id: str,
        payload: object,
        *,
        description: str | None = None,
        priority: int = 3,
        status: str = "pending",
        created_at: datetime | None = None,
    ) -> None:
        object.__setattr__(self, "_payload", payload)

        self.id = id
        self.description = description if description is not None else f"Задача {self.id}"
        self.priority = priority
        self.status = status
        self.created_at = created_at if created_at is not None else datetime.now(timezone.utc)

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        if name not in self._public_attributes:
            raise AttributeError(f"Задача не имеет публичного атрибута {name!r}")

        object.__setattr__(self, name, value)

    @property
    def payload(self) -> object:
        """Пользовательские данные, связанные с задачей."""
        return self._payload

    @payload.setter
    def payload(self, value: object) -> None:
        object.__setattr__(self, "_payload", value)

    @property
    def is_ready(self) -> bool:
        """Показывает, может ли задача быть взята в обработку."""
        return self.status == "pending"

    @property
    def is_terminal(self) -> bool:
        """Показывает, завершён ли жизненный цикл задачи."""
        return self.status in TaskStatusDescriptor.terminal_statuses

    def __repr__(self) -> str:
        return (
            "Task("
            f"id={self.id!r}, "
            f"payload={self.payload!r}, "
            f"description={self.description!r}, "
            f"priority={self.priority!r}, "
            f"status={self.status!r}, "
            f"created_at={self.created_at!r}"
            ")"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return NotImplemented

        return (
            self.id == other.id
            and self.payload == other.payload
            and self.description == other.description
            and self.priority == other.priority
            and self.status == other.status
            and self.created_at == other.created_at
        )
