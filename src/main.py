import asyncio
from pathlib import Path

from src.task_platform.async_executor import (
    AsyncTaskExecutor,
    AsyncTaskQueue,
    PayloadKindHandler,
)
from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.task_queue import TaskQueue
from src.task_platform.task_repr import Task


def main() -> None:
    """Демонстрационный вход в программу для асинхронного исполнителя из ЛР4."""
    demo_file = Path("demo_tasks.json")
    if not demo_file.exists():
        raise FileNotFoundError("Файл demo_tasks.json не найден")

    sources = [
        FileTaskSource(demo_file),
        GeneratorTaskSource(count=2, prefix="gen"),
        ApiStubTaskSource(
            [
                Task(
                    id="api-1",
                    payload={"kind": "sync"},
                    description="Получить задачи из API-заглушки",
                )
            ]
        ),
    ]

    queue = TaskQueue(intake_many(sources))

    print("Все задачи в очереди:")
    for task in queue:
        print(f"{task.summary} | ready={task.is_ready}")

    print("\nГотовые к выполнению задачи:")
    for task in queue.filter_by_status("pending"):
        print(task.summary)

    print("\nЗадачи с приоритетом не ниже 4:")
    for task in queue.filter_by_priority(4):
        print(task.summary)

    async_queue = AsyncTaskQueue(queue.filter_by_status("pending"))
    handlers = [
        PayloadKindHandler("email"),
        PayloadKindHandler("generated"),
        PayloadKindHandler("report"),
        PayloadKindHandler("sync"),
    ]

    print("\nАсинхронная обработка готовых задач:")
    results = asyncio.run(
        AsyncTaskExecutor(async_queue, handlers, worker_count=2).run()
    )
    for result in results:
        print(f"{result.task_id}: {result.status}")


if __name__ == "__main__":
    main()
