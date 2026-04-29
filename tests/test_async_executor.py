import asyncio
import logging

import pytest

from src.task_platform.async_executor import (
    AsyncTaskExecutor,
    AsyncTaskQueue,
    InvalidTaskHandlerError,
    PayloadKindHandler,
)
from src.task_platform.protocols import AsyncTaskHandler
from src.task_platform.task_repr import Task


class RecordingHandler:
    def __init__(self, kind: str = "email") -> None:
        self.kind = kind
        self.processed: list[str] = []

    def can_handle(self, task: Task) -> bool:
        return isinstance(task.payload, dict) and task.payload.get("kind") == self.kind

    async def handle(self, task: Task) -> None:
        await asyncio.sleep(0)
        self.processed.append(task.id)


class FailingHandler(RecordingHandler):
    async def handle(self, task: Task) -> None:
        await asyncio.sleep(0)
        raise RuntimeError(f"broken task {task.id}")


class ResourceHandler(RecordingHandler):
    def __init__(self) -> None:
        super().__init__()
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> "ResourceHandler":
        self.entered = True
        return self

    async def __aexit__(self, *args: object) -> None:
        self.exited = True


class NonAwaitableHandler:
    def can_handle(self, task: Task) -> bool:
        return True

    def handle(self, task: Task) -> None:
        return None


class InvalidHandler:
    handle = []


def test_async_task_handler_supports_runtime_protocol_check() -> None:
    assert isinstance(RecordingHandler(), AsyncTaskHandler)
    assert not isinstance(InvalidHandler(), AsyncTaskHandler)


def test_async_queue_puts_and_gets_tasks() -> None:
    async def scenario() -> None:
        task = Task(id="task-1", payload={"kind": "email"})
        queue = AsyncTaskQueue()

        await queue.put(task)

        assert len(queue) == 1
        assert await queue.get() == task
        queue.task_done()
        await queue.join()
        assert queue.empty()

    asyncio.run(scenario())


def test_async_queue_supports_async_iteration() -> None:
    async def scenario() -> None:
        queue = AsyncTaskQueue(
            [
                Task(id="task-1", payload={"kind": "email"}),
                Task(id="task-2", payload={"kind": "sync"}),
            ]
        )

        task_ids = [task.id async for task in queue]

        assert task_ids == ["task-1", "task-2"]
        assert queue.empty()
        await queue.join()

    asyncio.run(scenario())


def test_async_queue_accepts_only_task_instances() -> None:
    queue = AsyncTaskQueue()

    with pytest.raises(TypeError, match="только экземпляры Task"):
        queue.put_nowait("not a task")  # type: ignore[arg-type]


def test_executor_processes_tasks_with_matching_handlers() -> None:
    async def scenario() -> None:
        tasks = [
            Task(id="task-1", payload={"kind": "email"}),
            Task(id="task-2", payload={"kind": "email"}),
        ]
        queue = AsyncTaskQueue(tasks)
        handler = RecordingHandler()

        results = await AsyncTaskExecutor(queue, [handler], worker_count=2).run()

        assert {result.task_id for result in results} == {"task-1", "task-2"}
        assert all(result.successful for result in results)
        assert {task.status for task in tasks} == {"completed"}
        assert handler.processed == ["task-1", "task-2"]

    asyncio.run(scenario())


def test_executor_marks_failed_tasks_and_logs_errors(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> tuple[Task, list[object]]:
        task = Task(id="task-3", payload={"kind": "email"})
        queue = AsyncTaskQueue([task])

        with caplog.at_level(logging.ERROR, logger="task_platform.async_executor"):
            results = await AsyncTaskExecutor(queue, [FailingHandler()]).run()

        return task, results

    task, results = asyncio.run(scenario())

    assert task.status == "failed"
    assert results[0].status == "failed"
    assert isinstance(results[0].error, RuntimeError)
    assert "Ошибка обработки задачи task-3" in caplog.text


def test_executor_skips_tasks_without_handler(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> tuple[Task, list[object]]:
        task = Task(id="task-4", payload={"kind": "report"})
        queue = AsyncTaskQueue([task])

        with caplog.at_level(logging.WARNING, logger="task_platform.async_executor"):
            results = await AsyncTaskExecutor(queue, [RecordingHandler("email")]).run()

        return task, results

    task, results = asyncio.run(scenario())

    assert task.status == "pending"
    assert results[0].status == "skipped"
    assert "не найден обработчик" in caplog.text


def test_executor_uses_async_context_manager_for_handler_resources() -> None:
    async def scenario() -> ResourceHandler:
        task = Task(id="task-5", payload={"kind": "email"})
        handler = ResourceHandler()

        async with AsyncTaskExecutor(AsyncTaskQueue([task]), [handler]) as executor:
            assert handler.entered is True
            await executor.run()

        return handler

    handler = asyncio.run(scenario())

    assert handler.exited is True
    assert handler.processed == ["task-5"]


def test_executor_rejects_invalid_handlers() -> None:
    with pytest.raises(InvalidTaskHandlerError, match="AsyncTaskHandler"):
        AsyncTaskExecutor(AsyncTaskQueue(), [InvalidHandler()])  # type: ignore[list-item]


def test_executor_rejects_non_awaitable_handle_result() -> None:
    async def scenario() -> None:
        task = Task(id="task-6", payload=None)
        results = await AsyncTaskExecutor(
            AsyncTaskQueue([task]),
            [NonAwaitableHandler()],  # type: ignore[list-item]
        ).run()

        assert task.status == "failed"
        assert results[0].status == "failed"
        assert isinstance(results[0].error, InvalidTaskHandlerError)

    asyncio.run(scenario())


def test_payload_kind_handler_routes_by_payload_kind() -> None:
    async def scenario() -> PayloadKindHandler:
        handler = PayloadKindHandler("sync")
        tasks = [
            Task(id="task-7", payload={"kind": "sync"}),
            Task(id="task-8", payload={"kind": "email"}),
        ]

        await AsyncTaskExecutor(AsyncTaskQueue(tasks), [handler]).run()

        return handler

    handler = asyncio.run(scenario())

    assert handler.processed_tasks == ["task-7"]
