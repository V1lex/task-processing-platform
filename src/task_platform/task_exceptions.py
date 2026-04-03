class TaskError(ValueError):
    """Базовая ошибка модели задачи."""


class TaskFieldError(TaskError):
    """Базовая ошибка некорректного значения поля задачи."""

    def __init__(self, field_name: str, message: str) -> None:
        self.field_name = field_name
        super().__init__(f"{field_name}: {message}")


class TaskIdError(TaskFieldError):
    """Некорректный идентификатор задачи."""

    def __init__(self, message: str) -> None:
        super().__init__("id", message)


class TaskDescriptionError(TaskFieldError):
    """Некорректное описание задачи."""

    def __init__(self, message: str) -> None:
        super().__init__("description", message)


class TaskPriorityError(TaskFieldError):
    """Некорректный приоритет задачи."""

    def __init__(self, message: str) -> None:
        super().__init__("priority", message)


class TaskStatusError(TaskFieldError):
    """Некорректный статус задачи."""

    def __init__(self, message: str) -> None:
        super().__init__("status", message)


class TaskCreatedAtError(TaskFieldError):
    """Некорректное время создания задачи."""

    def __init__(self, message: str) -> None:
        super().__init__("created_at", message)


class TaskImmutableFieldError(TaskFieldError):
    """Попытка изменить неизменяемое поле задачи."""

    def __init__(self, field_name: str) -> None:
        super().__init__(field_name, "поле можно установить только один раз")


class TaskStateTransitionError(TaskStatusError):
    """Недопустимый переход между статусами задачи."""

    def __init__(self, current_status: str, next_status: str) -> None:
        super().__init__(
            f"переход из статуса {current_status!r} в статус {next_status!r} запрещён"
        )
