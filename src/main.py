from pathlib import Path

from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.task_queue import TaskQueue
from src.task_platform.task_repr import Task


def main() -> None:
    """Демонстрационный вход в программу для очереди задач из ЛР3."""
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
                    payload={"source": "api"},
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


if __name__ == "__main__":
    main()
