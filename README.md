# Лабораторная работа №1: Источники задач и контракты

## Цель
Реализовать подсистему приёма задач для платформы обработки задач через единый контракт `TaskSource` на базе `typing.Protocol`.

## Что сделано
- `TaskSource(Protocol)` с `@runtime_checkable`: `src/task_platform/protocols.py`
- Минимальное представление задачи (`id` + `payload`): `src/task_platform/task_repr.py`
- Источники задач:
  - файл: `src/task_platform/sources/file_source.py`
  - генератор: `src/task_platform/sources/generator_source.py`
  - API-заглушка: `src/task_platform/sources/api_stub_source.py`
- Intake-модуль с runtime-проверкой контракта: `src/task_platform/intake.py`

## Быстрый запуск через Docker

### 1) Сборка образа
```bash
docker build -t task-platform-lab1 .
```

### 2) Запуск демо
```bash
docker run --rm task-platform-lab1
```

Команда запускает `src/main.py` внутри контейнера.
Сейчас в демо для файлового источника используется `demo_tasks.json` из корня проекта.

### 3) Запуск тестов
```bash
docker run --rm task-platform-lab1 pytest -q
```

Проверка покрытия (минимум 80%):
```bash
docker run --rm task-platform-lab1 pytest --cov=src/task_platform --cov-report=term-missing --cov-fail-under=80
```

## Файловый источник: свой JSON-файл

`FileTaskSource` может читать не только `demo_tasks.json`, но и любой другой JSON-файл похожей структуры.

Пример допустимого файла:

```json
[
  {"id": "custom-1", "payload": {"kind": "email", "to": "user@example.com"}},
  {"id": "custom-2", "payload": {"kind": "report", "period": "2026-03"}}
]
```

Важно, чтобы корневой элемент был списком, а также, чтобы каждый элемент содержал поля `id` и `payload`.

## Пример работы

### 1) Подготовьте входной файл
Создайте `tasks.json` в корне проекта:

```json
[
  {"id": "file-1", "payload": {"kind": "email", "to": "user@example.com"}},
  {"id": "file-2", "payload": {"kind": "report", "period": "2026-03"}}
]
```

### 2) Запустите интерактивный сценарий в контейнере
```bash
docker run --rm -i -v "$PWD":/app -w /app task-platform-lab1 python - <<'PY'
from src.task_platform.intake import intake_many
from src.task_platform.sources.file_source import FileTaskSource
from src.task_platform.sources.generator_source import GeneratorTaskSource
from src.task_platform.sources.api_stub_source import ApiStubTaskSource
from src.task_platform.task_repr import Task

sources = [
    FileTaskSource("tasks.json"),
    GeneratorTaskSource(count=2, prefix="gen"),
    ApiStubTaskSource([
        Task(id="api-1", payload={"kind": "sync", "target": "crm"}),
    ]),
]

tasks = intake_many(sources)
for task in tasks:
    print(task.id, task.payload)
PY
```

### 3) Что делает пример
- `FileTaskSource` читает задачи из `tasks.json`.
- `GeneratorTaskSource` добавляет сгенерированные задачи (`gen-0`, `gen-1`).
- `ApiStubTaskSource` имитирует внешний API и возвращает подготовленные задачи.
- `intake_many(...)` объединяет задачи из всех источников через контракт `TaskSource`.

### 4) Вывод
```
file-1 {'kind': 'email', 'to': 'user@example.com'}
file-2 {'kind': 'report', 'period': '2026-03'}
gen-0 {'index': 0}
gen-1 {'index': 1}
api-1 {'kind': 'sync', 'target': 'crm'}
```
