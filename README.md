# Лабораторная работа №3. Очередь задач: итераторы и генераторы

## Цель
Реализовать пользовательскую коллекцию `TaskQueue` для платформы обработки задач с повторяемой итерацией и ленивой фильтрацией задач.

## Что сделано
- `TaskQueue` как коллекция задач с повторным обходом: `src/task_platform/task_queue.py`
- `TaskQueueIterator` с явной реализацией `__iter__` и `__next__`: `src/task_platform/task_queue.py`
- Ленивые фильтры `filter_by_status(...)` и `filter_by_priority(...)` на базе генераторов: `src/task_platform/task_queue.py`
- Совместимость очереди со стандартными конструкциями `for`, `list(...)`, `sum(...)`
- Сохранена совместимость с ЛР1 и ЛР2: источники задач и модель `Task` используются без перелома API

## Быстрый запуск через Docker

### 1) Сборка образа
```bash
docker build -t task-platform-lab3 .
```

### 2) Запуск демо
```bash
docker run --rm task-platform-lab3
```

Команда запускает `src.main` в контейнере.
В демо используется `demo_tasks.json` из корня проекта.

### 3) Запуск тестов
```bash
docker run --rm task-platform-lab3 python -m pytest -q
```

Проверка покрытия (минимум 80%):
```bash
docker run --rm task-platform-lab3 python -m pytest --cov=src/task_platform --cov-report=term-missing --cov-fail-under=80
```

## Использование `TaskQueue`

`TaskQueue` принимает готовые объекты `Task`, поддерживает повторную итерацию и не создаёт лишних списков при фильтрации.

Пример:

```python
from src.task_platform.task_queue import TaskQueue
from src.task_platform.task_repr import Task

queue = TaskQueue(
    [
        Task(id="task-1", payload={"kind": "email"}, description="Отправить письмо", priority=5),
        Task(id="task-2", payload={"kind": "report"}, description="Подготовить отчёт", priority=3, status="in_progress"),
        Task(id="task-3", payload={"kind": "sync"}, description="Синхронизировать CRM", priority=4),
    ]
)

all_tasks = list(queue)
priority_sum = sum(task.priority for task in queue)
ready_tasks = list(queue.filter_by_status("pending"))
important_tasks = list(queue.filter_by_priority(4))
```

Важно:
- каждый вызов `iter(queue)` возвращает новый итератор, поэтому очередь можно обходить повторно;
- `filter_by_status(...)` и `filter_by_priority(...)` возвращают генераторы, а не списки;
- фильтр по статусу нормализует алиасы `new` и `done` через ту же схему статусов, что и модель `Task`;
- `filter_by_priority(n)` возвращает задачи с приоритетом не ниже `n`.

## Пример работы

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
docker run --rm -i -v "$PWD":/app -w /app task-platform-lab3 python - <<'PY'
from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.task_queue import TaskQueue
from src.task_platform.task_repr import Task

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

print("Повторный обход очереди:")
for task in queue:
    print(task.summary)

print("\nГотовые задачи:")
for task in queue.filter_by_status("pending"):
    print(task.summary)

print("\nПриоритет 4 и выше:")
for task in queue.filter_by_priority(4):
    print(task.summary)
PY
```

### 3) Что делает пример
- принимает задачи из файлового источника, генератора и API-заглушки;
- складывает их в `TaskQueue`;
- показывает повторный обход коллекции;
- выполняет ленивую фильтрацию по статусу и приоритету.

### 4) Вывод
```
Повторный обход очереди:
file-1 [pending, p4] Отправить письмо пользователю
file-2 [in_progress, p2] Подготовить отчёт
gen-0 [pending, p3] Сгенерированная задача 0
gen-1 [pending, p3] Сгенерированная задача 1
api-1 [pending, p5] Синхронизировать CRM

Готовые задачи:
file-1 [pending, p4] Отправить письмо пользователю
gen-0 [pending, p3] Сгенерированная задача 0
gen-1 [pending, p3] Сгенерированная задача 1
api-1 [pending, p5] Синхронизировать CRM

Приоритет 4 и выше:
file-1 [pending, p4] Отправить письмо пользователю
api-1 [pending, p5] Синхронизировать CRM
```
