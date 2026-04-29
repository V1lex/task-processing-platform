# Лабораторная работа №4. Асинхронный исполнитель задач

## Цель
Реализовать асинхронную систему обработки задач поверх платформы из ЛР1-3: источники задач, доменная модель `Task` и повторяемая очередь `TaskQueue` сохраняются, а выполнение задач переносится в `asyncio`.

## Что сделано
- `AsyncTaskQueue` как асинхронная очередь задач на базе `asyncio.Queue`: `src/task_platform/async_executor.py`
- `AsyncTaskHandler` как `typing.Protocol` с `@runtime_checkable`: `src/task_platform/protocols.py`
- `AsyncTaskExecutor` как асинхронный контекстный менеджер с пулом workers: `src/task_platform/async_executor.py`
- Маршрутизация задач по расширяемым обработчикам через `can_handle(task)`
- Централизованное логирование успешной обработки, пропусков и ошибок
- Сохранён жизненный цикл задачи из ЛР2: `pending -> in_progress -> completed | failed | cancelled`
- Покрыты тестами успешная обработка, ошибки, отсутствие обработчика, runtime-контракт и управление ресурсами обработчика

## Быстрый запуск через Docker

### 1) Сборка образа
```bash
docker build -t task-platform-lab4 .
```

### 2) Запуск демо
```bash
docker run --rm task-platform-lab4
```

Команда запускает `src.main` в контейнере.
В демо используется `demo_tasks.json` из корня проекта.

### 3) Запуск тестов
```bash
docker run --rm task-platform-lab4 python -m pytest -q
```

Проверка покрытия:
```bash
docker run --rm task-platform-lab4 python -m pytest --cov=src/task_platform --cov-report=term-missing --cov-fail-under=80
```

Локально через `uv`:
```bash
uv run --extra test python -m pytest --cov=src/task_platform --cov-report=term-missing --cov-fail-under=80 -q
```

## Основные сущности

### `AsyncTaskHandler`
Асинхронный обработчик не обязан наследоваться от базового класса. Достаточно реализовать контракт:

```python
from src.task_platform.task_repr import Task


class EmailHandler:
    def can_handle(self, task: Task) -> bool:
        return isinstance(task.payload, dict) and task.payload.get("kind") == "email"

    async def handle(self, task: Task) -> None:
        ...
```

Контракт проверяется структурно:

```python
from src.task_platform.protocols import AsyncTaskHandler

assert isinstance(EmailHandler(), AsyncTaskHandler)
```

### `AsyncTaskQueue`
Очередь принимает только `Task` и использует неблокирующие операции `asyncio`:

```python
from src.task_platform.async_executor import AsyncTaskQueue
from src.task_platform.task_repr import Task

queue = AsyncTaskQueue()
await queue.put(Task(id="task-1", payload={"kind": "email"}))

async for task in queue:
    ...
```

### `AsyncTaskExecutor`
Исполнитель берёт задачи из очереди, выбирает первый подходящий обработчик и централизованно управляет статусами:

```python
from src.task_platform.async_executor import AsyncTaskExecutor, AsyncTaskQueue
from src.task_platform.task_repr import Task

tasks = [
    Task(id="email-1", payload={"kind": "email"}),
    Task(id="sync-1", payload={"kind": "sync"}),
]

queue = AsyncTaskQueue(tasks)

async with AsyncTaskExecutor(queue, [EmailHandler(), SyncHandler()], worker_count=2) as executor:
    results = await executor.run()
```

Правила обработки:
- задача в статусе `pending` переводится в `in_progress`;
- при успешном `handle(task)` задача становится `completed`, если обработчик не завершил её сам;
- при исключении задача становится `failed`, ошибка попадает в `TaskExecutionResult` и логируется;
- задача без подходящего обработчика пропускается без изменения статуса;
- задачи не в `pending` пропускаются, чтобы не нарушать инварианты модели.

## Пример полного сценария

```python
import asyncio

from src.task_platform.async_executor import AsyncTaskExecutor, AsyncTaskQueue, PayloadKindHandler
from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.task_repr import Task


async def run() -> None:
    tasks = intake_many(
        [
            GeneratorTaskSource(count=2, prefix="gen"),
            ApiStubTaskSource(
                [
                    Task(
                        id="api-sync",
                        payload={"kind": "sync"},
                        description="Синхронизировать CRM",
                        priority=5,
                    )
                ]
            ),
        ]
    )

    queue = AsyncTaskQueue(tasks)
    handlers = [
        PayloadKindHandler("sync"),
        PayloadKindHandler("email"),
        PayloadKindHandler("generated"),
    ]

    results = await AsyncTaskExecutor(queue, handlers, worker_count=2).run()

    for result in results:
        print(result.task_id, result.status)


asyncio.run(run())
```

## Проверенный результат

На момент сдачи:

```text
39 passed
Total coverage: 93.12%
```
