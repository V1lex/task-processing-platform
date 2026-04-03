# Лабораторная работа №2. Модель задачи: дескрипторы и `@property`

## Цель
Реализовать доменную модель `Task` для платформы обработки задач с корректной инкапсуляцией, валидацией состояния и чистым публичным API.

## Что сделано
- Класс `Task` с разделением публичного API и внутреннего состояния: `src/task_platform/task_repr.py`
- Пользовательские дескрипторы данных (`data descriptors`) для `id`, `description`, `priority`, `status`, `created_at`: `src/task_platform/task_descriptors.py`
- Дескриптор без метода `__set__` (`non-data descriptor`) для `summary`, показывающий различия между типами дескрипторов: `src/task_platform/task_descriptors.py`
- `@property` для защищённого доступа к `payload` и вычисляемых свойств (`computed properties`) `is_ready`, `is_terminal`
- Специализированные исключения для нарушения инвариантов: `src/task_platform/task_exceptions.py`
- Дополнительная проверка контракта источников: intake-модуль проверяет вызываемость `get_tasks()` и состав возвращаемого списка
- Совместимость со слоем источников задач: файловый источник умеет читать расширенную модель из JSON

## Быстрый запуск через Docker

### 1) Сборка образа
```bash
docker build -t task-platform-lab2 .
```

### 2) Запуск демо
```bash
docker run --rm task-platform-lab2
```

Команда запускает модуль `src.main` в контейнере.
В демо используется `demo_tasks.json` из корня проекта.

### 3) Запуск тестов
```bash
docker run --rm task-platform-lab2 python -m pytest -q
```

Проверка покрытия (минимум 80%):
```bash
docker run --rm task-platform-lab2 python -m pytest --cov=src/task_platform --cov-report=term-missing --cov-fail-under=80
```

## Формат JSON для `Task`

`FileTaskSource` поддерживает как минимальные записи из ЛР1, так и расширенные поля модели задачи.

Пример допустимого файла:

```json
[
  {
    "id": "task-1",
    "payload": {"kind": "email", "to": "user@example.com"},
    "description": "Отправить приветственное письмо",
    "priority": 5,
    "status": "new",
    "created_at": "2026-04-02T09:30:00+00:00"
  },
  {
    "id": "task-2",
    "payload": {"kind": "report", "period": "2026-03"},
    "description": "Подготовить ежемесячный отчёт",
    "priority": 3
  }
]
```

Важно:
- `id` и `description` не могут быть пустыми;
- `priority` должен быть в диапазоне от `1` до `5`;
- `status` нормализуется к одному из значений: `pending`, `in_progress`, `completed`, `failed`, `cancelled`.

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
  }
]
```

### 2) Запустите интерактивный сценарий в контейнере
```bash
docker run --rm -i -v "$PWD":/app -w /app task-platform-lab2 python - <<'PY'
from src.task_platform.intake import intake_many
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
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
            ),
        ]
    ),
]

tasks = intake_many(sources)
for task in tasks:
    print(task.summary, "| ready=", task.is_ready, sep="")
PY
```

### 3) Что делает пример
- `FileTaskSource` загружает задачу из `tasks.json`;
- `GeneratorTaskSource` добавляет сгенерированные задачи;
- `ApiStubTaskSource` возвращает подготовленную задачу;
- `summary` показывает работу дескриптора без метода `__set__` (`non-data descriptor`);
- `is_ready` вычисляется через `@property` как вычисляемое свойство (`computed property`).

### 4) Вывод
```
file-1 [pending, p4] Отправить письмо пользователю | ready=True
gen-0 [pending, p3] Сгенерированная задача 0 | ready=True
gen-1 [pending, p3] Сгенерированная задача 1 | ready=True
api-1 [pending, p3] Синхронизировать CRM | ready=True
```
