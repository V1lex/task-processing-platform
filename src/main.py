from pathlib import Path

from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.task_repr import Task


def main() -> None:
    """Демонстрационный вход в программу для модели задачи из ЛР2."""
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

    tasks = intake_many(sources)
    for task in tasks:
        print(f"{task.summary} | ready={task.is_ready}")


if __name__ == "__main__":
    main()
