from datetime import datetime, timezone

from src.task_platform.task_exceptions import (
    TaskCreatedAtError,
    TaskDescriptionError,
    TaskIdError,
    TaskImmutableFieldError,
    TaskPriorityError,
    TaskStateTransitionError,
    TaskStatusError,
)

_MISSING = object()  # Специальный маркер для отсутствующих значений в дескрипторах


class ValidatedDataDescriptor:
    """Базовый дескриптор данных с валидацией значения."""

    __slots__ = ("_allow_reassignment", "public_name", "storage_name")

    def __init__(self, *, allow_reassignment: bool = True) -> None:
        self._allow_reassignment = allow_reassignment
        self.public_name = ""
        self.storage_name = ""

    def __set_name__(self, owner: type[object], name: str) -> None:
        self.public_name = name
        self.storage_name = f"_{name}"

    def __get__(self, instance: object | None, owner: type[object] | None = None) -> object:
        if instance is None:
            return self
        return getattr(instance, self.storage_name)

    def __set__(self, instance: object, value: object) -> None:
        current_value = getattr(instance, self.storage_name, _MISSING)
        if current_value is not _MISSING and not self._allow_reassignment:
            raise TaskImmutableFieldError(self.public_name)

        validated_value = self.validate(instance, value, current_value)
        object.__setattr__(instance, self.storage_name, validated_value)

    def validate(
        self,
        instance: object,
        value: object,
        current_value: object,
    ) -> object:
        return value


class TaskIdDescriptor(ValidatedDataDescriptor):
    """Идентификатор задачи, который нельзя изменить после инициализации."""

    def __init__(self) -> None:
        super().__init__(allow_reassignment=False)

    def validate(
        self,
        instance: object,
        value: object,
        current_value: object,
    ) -> str:
        if not isinstance(value, str):
            raise TaskIdError("ожидается строка")

        normalized_value = value.strip()
        if not normalized_value:
            raise TaskIdError("идентификатор не может быть пустым")

        return normalized_value


class TaskDescriptionDescriptor(ValidatedDataDescriptor):
    """Описание задачи с защитой от пустых значений."""

    def validate(
        self,
        instance: object,
        value: object,
        current_value: object,
    ) -> str:
        if not isinstance(value, str):
            raise TaskDescriptionError("ожидается строка")

        normalized_value = value.strip()
        if not normalized_value:
            raise TaskDescriptionError("описание не может быть пустым")

        return normalized_value


class TaskPriorityDescriptor(ValidatedDataDescriptor):
    """Приоритет задачи в диапазоне от 1 до 5."""

    def validate(
        self,
        instance: object,
        value: object,
        current_value: object,
    ) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TaskPriorityError("ожидается целое число от 1 до 5")

        if value < 1 or value > 5:
            raise TaskPriorityError("приоритет должен быть в диапазоне от 1 до 5")

        return value


class TaskStatusDescriptor(ValidatedDataDescriptor):
    """Статус задачи с контролем допустимых переходов."""

    aliases = {
        "done": "completed",
        "error": "failed",
        "finished": "completed",
        "new": "pending",
        "queued": "pending",
        "ready": "pending",
    }
    allowed_statuses = frozenset(
        {"pending", "in_progress", "completed", "failed", "cancelled"}
    )
    terminal_statuses = frozenset({"completed", "failed", "cancelled"})
    transitions = {
        "pending": frozenset({"in_progress", "cancelled"}),
        "in_progress": frozenset({"completed", "failed", "cancelled"}),
        "completed": frozenset(),
        "failed": frozenset(),
        "cancelled": frozenset(),
    }

    def validate(
        self,
        instance: object,
        value: object,
        current_value: object,
    ) -> str:
        if not isinstance(value, str):
            raise TaskStatusError("ожидается строка")

        normalized_value = value.strip().lower()
        if not normalized_value:
            raise TaskStatusError("статус не может быть пустым")

        normalized_value = self.aliases.get(normalized_value, normalized_value)
        if normalized_value not in self.allowed_statuses:
            allowed_values = ", ".join(sorted(self.allowed_statuses))
            raise TaskStatusError(
                f"неподдерживаемый статус {normalized_value!r}; допустимые значения: {allowed_values}"
            )

        if current_value is _MISSING or normalized_value == current_value:
            return normalized_value

        if normalized_value not in self.transitions[current_value]:
            raise TaskStateTransitionError(current_value, normalized_value)

        return normalized_value


class TaskCreatedAtDescriptor(ValidatedDataDescriptor):
    """Время создания задачи, фиксируемое при инициализации."""

    def __init__(self) -> None:
        super().__init__(allow_reassignment=False)

    def validate(
        self,
        instance: object,
        value: object,
        current_value: object,
    ) -> datetime:
        if not isinstance(value, datetime):
            raise TaskCreatedAtError("ожидается datetime")

        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)


class TaskSummaryDescriptor:
    """Пример дескриптора без `__set__` для краткого представления задачи."""

    def __get__(self, instance: object | None, owner: type[object] | None = None) -> str:
        if instance is None:
            return self

        return (
            f"{instance.id} [{instance.status}, p{instance.priority}] "
            f"{instance.description}"
        )
