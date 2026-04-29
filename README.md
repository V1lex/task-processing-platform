# Платформа обработки задач

Платформа обработки задач на Python. Проект показывает, как постепенно построить систему приёма, хранения и выполнения задач с использованием объектной модели Python, протоколов, дескрипторов, итераторов, генераторов и `asyncio`.

Задача в проекте — это единица работы с идентификатором, пользовательскими данными, описанием, приоритетом, статусом и временем создания. Задачи могут приходить из разных источников, складываться в очереди, фильтроваться и обрабатываться синхронно или асинхронно.

## Возможности

- Приём задач из независимых источников без общего базового класса.
- Контракты через `typing.Protocol` и runtime-проверки.
- Доменная модель `Task` с дескрипторами, `property`, валидацией и специализированными исключениями.
- Повторяемая синхронная очередь `TaskQueue` с пользовательским итератором и ленивыми фильтрами.
- Асинхронная очередь `AsyncTaskQueue` на базе `asyncio.Queue` с поддержкой `async for`.
- Асинхронный исполнитель `AsyncTaskExecutor` с расширяемыми обработчиками задач.
- Асинхронные контекстные менеджеры для управления ресурсами обработчиков.
- Централизованное логирование и обработка ошибок.

## Структура проекта

```text
src/
  main.py                         # демонстрационный запуск платформы
  task_platform/
    async_executor.py             # AsyncTaskQueue, AsyncTaskExecutor, обработчики
    intake.py                     # приём задач из источников
    protocols.py                  # TaskSource и AsyncTaskHandler
    task_descriptors.py           # дескрипторы модели Task
    task_exceptions.py            # доменные исключения
    task_queue.py                 # TaskQueue и TaskQueueIterator
    task_repr.py                  # модель Task
    sources/
      api_stub_source.py          # API-заглушка
      file_source.py              # JSON-файл
      generator_source.py         # программная генерация задач
tests/                            # тесты платформы
demo_tasks.json                   # демонстрационные задачи
```

## Быстрый запуск через Docker

### 1) Сборка образа

```bash
docker build -t task-platform .
```

### 2) Запуск демо

```bash
docker run --rm task-platform
```

Команда запускает `src.main`. В демо используются задачи из `demo_tasks.json`, генератор задач и API-заглушка.

### 3) Запуск тестов

```bash
docker run --rm task-platform python -m pytest -q
```

Проверка покрытия:

```bash
docker run --rm task-platform python -m pytest --cov=src/task_platform --cov-report=term-missing --cov-fail-under=80
```

## Локальный запуск

Если используется `uv`:

```bash
uv run --extra test python -m pytest -q
uv run --extra test python -m pytest --cov=src/task_platform --cov-report=term-missing --cov-fail-under=80
```

Если зависимости уже установлены в окружении:

```bash
python -m src.main
python -m pytest -q
```

## Модель задачи

`Task` хранит основные данные задачи и защищает инварианты:

```python
from src.task_platform.task_repr import Task

task = Task(
    id="email-1",
    payload={"kind": "email", "to": "user@example.com"},
    description="Отправить письмо пользователю",
    priority=4,
    status="new",
)

print(task.id)
print(task.status)      # pending, потому что new нормализуется
print(task.is_ready)    # True
print(task.summary)     # email-1 [pending, p4] Отправить письмо пользователю
```

Основной жизненный цикл статусов:

```text
pending -> in_progress -> completed | failed | cancelled
pending -> cancelled
```

Некорректные значения полей приводят к доменным исключениям: `TaskIdError`, `TaskPriorityError`, `TaskStatusError`, `TaskStateTransitionError` и другим.

## Источники задач

Источник задач должен реализовать контракт `TaskSource`:

```python
from src.task_platform.task_repr import Task


class CustomSource:
    def get_tasks(self) -> list[Task]:
        return [Task(id="custom-1", payload={"kind": "sync"})]
```

Наследоваться от общего базового класса не нужно. Достаточно структурно соответствовать протоколу:

```python
from src.task_platform.protocols import TaskSource

source = CustomSource()
assert isinstance(source, TaskSource)
```

Готовые источники:

- `FileTaskSource` читает задачи из JSON-файла;
- `GeneratorTaskSource` программно создаёт задачи;
- `ApiStubTaskSource` имитирует внешний API.

Несколько источников можно объединить через `intake_many`:

```python
from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.task_repr import Task

tasks = intake_many(
    [
        GeneratorTaskSource(count=2, prefix="gen"),
        ApiStubTaskSource([Task(id="api-1", payload={"kind": "sync"})]),
    ]
)
```

## Синхронная очередь задач

`TaskQueue` — повторяемая коллекция задач. Её можно обходить через `for`, преобразовывать в `list`, использовать в выражениях `sum(...)` и фильтровать лениво.

```python
from src.task_platform.task_queue import TaskQueue
from src.task_platform.task_repr import Task

queue = TaskQueue(
    [
        Task(id="task-1", payload={"kind": "email"}, priority=5),
        Task(id="task-2", payload={"kind": "report"}, priority=3, status="in_progress"),
        Task(id="task-3", payload={"kind": "sync"}, priority=4),
    ]
)

all_tasks = list(queue)
priority_sum = sum(task.priority for task in queue)
ready_tasks = list(queue.filter_by_status("pending"))
important_tasks = list(queue.filter_by_priority(4))
```

Важно:

- каждый вызов `iter(queue)` возвращает новый `TaskQueueIterator`;
- `filter_by_status(...)` и `filter_by_priority(...)` возвращают генераторы;
- фильтр по статусу использует те же алиасы, что и модель `Task`;
- `filter_by_priority(n)` возвращает задачи с приоритетом не ниже `n`.

## Асинхронная очередь и исполнитель

`AsyncTaskQueue` использует `asyncio.Queue`, принимает только `Task` и поддерживает асинхронные операции:

```python
from src.task_platform.async_executor import AsyncTaskQueue
from src.task_platform.task_repr import Task

queue = AsyncTaskQueue()
await queue.put(Task(id="task-1", payload={"kind": "email"}))

async for task in queue:
    print(task.summary)
```

Обработчик задачи описывается протоколом `AsyncTaskHandler`:

```python
from src.task_platform.task_repr import Task


class EmailHandler:
    def can_handle(self, task: Task) -> bool:
        return isinstance(task.payload, dict) and task.payload.get("kind") == "email"

    async def handle(self, task: Task) -> None:
        ...
```

`AsyncTaskExecutor` выбирает первый подходящий обработчик, переводит задачу в `in_progress`, ждёт `handle(task)` и завершает задачу:

```python
from src.task_platform.async_executor import AsyncTaskExecutor, AsyncTaskQueue, PayloadKindHandler
from src.task_platform.task_repr import Task

tasks = [
    Task(id="email-1", payload={"kind": "email"}),
    Task(id="sync-1", payload={"kind": "sync"}),
]

queue = AsyncTaskQueue(tasks)
handlers = [
    PayloadKindHandler("email"),
    PayloadKindHandler("sync"),
]

results = await AsyncTaskExecutor(queue, handlers, worker_count=2).run()
```

Правила обработки:

- задача в статусе `pending` переводится в `in_progress`;
- при успешном выполнении обработчика задача становится `completed`, если обработчик не завершил её сам;
- при исключении задача становится `failed`, ошибка сохраняется в `TaskExecutionResult` и логируется;
- задача без подходящего обработчика пропускается без изменения статуса;
- задача не в `pending` пропускается, чтобы не нарушать инварианты модели.

## Полный пример работы

### 1) Подготовьте входной файл

Создайте `tasks.json` в корне проекта:

```json
[
  {
    "id": "file-1",
    "payload": {"kind": "email", "to": "user@example.com"},
    "description": "Отправить письмо пользователю",
    "priority": 4,
    "status": "new"
  },
  {
    "id": "file-2",
    "payload": {"kind": "report", "period": "2026-03"},
    "description": "Подготовить отчёт",
    "priority": 2,
    "status": "in_progress"
  }
]
```

### 2) Запустите интерактивный сценарий в контейнере

```bash
docker run --rm -i -v "$PWD":/app -w /app task-platform python - <<'PY'
import asyncio

from src.task_platform.async_executor import AsyncTaskExecutor, AsyncTaskQueue, PayloadKindHandler
from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.task_queue import TaskQueue
from src.task_platform.task_repr import Task


async def run() -> None:
    sources = [
        FileTaskSource("tasks.json"),
        GeneratorTaskSource(count=2, prefix="gen"),
        ApiStubTaskSource(
            [
                Task(
                    id="api-1",
                    payload={"kind": "sync", "target": "crm"},
                    description="Синхронизировать CRM",
                    priority=5,
                ),
            ]
        ),
    ]

    queue = TaskQueue(intake_many(sources))

    print("Повторный обход обычной очереди:")
    for task in queue:
        print(task.summary)

    print("\nАсинхронный обход готовых задач:")
    preview_queue = AsyncTaskQueue(queue.filter_by_status("pending"))
    async for task in preview_queue:
        print(task.summary)

    execution_queue = AsyncTaskQueue(queue.filter_by_status("pending"))
    handlers = [
        PayloadKindHandler("email"),
        PayloadKindHandler("generated"),
        PayloadKindHandler("sync"),
    ]

    results = await AsyncTaskExecutor(
        execution_queue,
        handlers,
        worker_count=1,
    ).run()

    print("\nРезультаты асинхронной обработки:")
    for result in results:
        print(f"{result.task_id}: {result.status}")

    print("\nФинальные статусы:")
    for task in queue:
        print(f"{task.id}: {task.status}")


asyncio.run(run())
PY
```

### 3) Что делает пример

- принимает задачи из файла, генератора и API-заглушки;
- складывает их в обычную повторяемую `TaskQueue`;
- создаёт `AsyncTaskQueue` для готовых задач и обходит её через `async for`;
- запускает `AsyncTaskExecutor` с расширяемыми обработчиками;
- переводит успешно обработанные задачи в `completed`;
- оставляет задачу со статусом `in_progress` без изменений.

### 4) Ожидаемый вывод

```text
Повторный обход обычной очереди:
file-1 [pending, p4] Отправить письмо пользователю
file-2 [in_progress, p2] Подготовить отчёт
gen-0 [pending, p3] Сгенерированная задача 0
gen-1 [pending, p3] Сгенерированная задача 1
api-1 [pending, p5] Синхронизировать CRM

Асинхронный обход готовых задач:
file-1 [pending, p4] Отправить письмо пользователю
gen-0 [pending, p3] Сгенерированная задача 0
gen-1 [pending, p3] Сгенерированная задача 1
api-1 [pending, p5] Синхронизировать CRM

Результаты асинхронной обработки:
file-1: completed
gen-0: completed
gen-1: completed
api-1: completed

Финальные статусы:
file-1: completed
file-2: in_progress
gen-0: completed
gen-1: completed
api-1: completed
```
