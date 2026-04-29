import asyncio
import inspect
import logging
from collections.abc import Iterable, Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass
from types import TracebackType
from typing import Literal

from src.task_platform.protocols import AsyncTaskHandler
from src.task_platform.task_repr import Task

TaskExecutionStatus = Literal["completed", "failed", "skipped"]

_STOP_WORKER = object()


class InvalidTaskHandlerError(TypeError):
    """Выбрасывается, когда обработчик не соблюдает AsyncTaskHandler."""


@dataclass(frozen=True)
class TaskExecutionResult:
    """Итог обработки одной задачи."""

    task_id: str
    status: TaskExecutionStatus
    handler_name: str | None = None
    error: BaseException | None = None

    @property
    def successful(self) -> bool:
        """Показывает, что задача была обработана без ошибок."""
        return self.status == "completed"


class AsyncTaskQueue:
    """Асинхронная очередь задач на базе asyncio.Queue."""

    def __init__(self, tasks: Iterable[Task] = (), *, maxsize: int = 0) -> None:
        self._queue: asyncio.Queue[Task | object] = asyncio.Queue(maxsize=maxsize)
        for task in tasks:
            self.put_nowait(task)

    def __len__(self) -> int:
        return self.qsize()

    def empty(self) -> bool:
        """Показывает, пуста ли очередь прямо сейчас."""
        return self._queue.empty()

    def qsize(self) -> int:
        """Возвращает текущий размер очереди."""
        return self._queue.qsize()

    async def put(self, task: Task) -> None:
        """Асинхронно добавляет задачу в очередь."""
        await self._queue.put(self._ensure_task(task))

    def put_nowait(self, task: Task) -> None:
        """Добавляет задачу в очередь без ожидания свободного места."""
        self._queue.put_nowait(self._ensure_task(task))

    async def extend(self, tasks: Iterable[Task]) -> None:
        """Асинхронно добавляет последовательность задач."""
        for task in tasks:
            await self.put(task)

    async def get(self) -> Task:
        """Асинхронно извлекает следующую задачу."""
        item = await self._queue.get()
        if item is _STOP_WORKER:
            self._queue.task_done()
            raise RuntimeError("служебный маркер исполнителя не является задачей")
        return item

    def task_done(self) -> None:
        """Сообщает очереди, что ранее полученная задача завершена."""
        self._queue.task_done()

    async def join(self) -> None:
        """Ожидает завершения всех задач, извлечённых из очереди."""
        await self._queue.join()

    async def _put_stop_marker(self) -> None:
        await self._queue.put(_STOP_WORKER)

    async def _get_raw(self) -> Task | object:
        return await self._queue.get()

    def _ensure_task(self, task: Task) -> Task:
        if not isinstance(task, Task):
            raise TypeError("Асинхронная очередь принимает только экземпляры Task")
        return task


class AsyncTaskExecutor:
    """Асинхронный исполнитель задач с расширяемыми обработчиками."""

    def __init__(
        self,
        queue: AsyncTaskQueue,
        handlers: Sequence[AsyncTaskHandler],
        *,
        worker_count: int = 1,
        logger: logging.Logger | None = None,
    ) -> None:
        if worker_count < 1:
            raise ValueError("worker_count должен быть положительным")

        self._queue = queue
        self._handlers = [self._validate_handler(handler) for handler in handlers]
        if not self._handlers:
            raise ValueError("нужен хотя бы один обработчик задач")

        self._worker_count = worker_count
        self._logger = logger or logging.getLogger("task_platform.async_executor")
        self._exit_stack = AsyncExitStack()
        self._entered = False
        self._running = False
        self._workers: list[asyncio.Task[None]] = []
        self._results: list[TaskExecutionResult] = []

    async def __aenter__(self) -> "AsyncTaskExecutor":
        for handler in self._handlers:
            await self._enter_handler_context(handler)
        self._entered = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        await self._stop_workers()
        self._entered = False
        return await self._exit_stack.__aexit__(exc_type, exc, traceback)

    async def run(self) -> list[TaskExecutionResult]:
        """Обрабатывает все задачи, которые есть в очереди на момент запуска."""
        if not self._entered:
            async with self:
                return await self.run()

        if self._running:
            raise RuntimeError("исполнитель уже запущен")

        self._running = True
        self._results = []
        self._workers = [
            asyncio.create_task(self._worker_loop(index), name=f"task-worker-{index}")
            for index in range(self._worker_count)
        ]

        await self._queue.join()
        await self._stop_workers()
        self._running = False
        return list(self._results)

    async def _worker_loop(self, _index: int) -> None:
        while True:
            item = await self._queue._get_raw()
            try:
                if item is _STOP_WORKER:
                    return
                await self._process_task(item)
            finally:
                self._queue.task_done()

    async def _process_task(self, task: Task) -> None:
        if not task.is_ready:
            self._logger.info("Задача %s пропущена: статус %s", task.id, task.status)
            self._results.append(TaskExecutionResult(task.id, "skipped"))
            return

        handler = self._find_handler(task)
        if handler is None:
            self._logger.warning("Для задачи %s не найден обработчик", task.id)
            self._results.append(TaskExecutionResult(task.id, "skipped"))
            return

        handler_name = type(handler).__name__
        try:
            task.status = "in_progress"
            await self._call_handler(handler, task)
            if not task.is_terminal:
                task.status = "completed"
            self._logger.info("Задача %s успешно обработана", task.id)
            self._results.append(TaskExecutionResult(task.id, "completed", handler_name))
        except Exception as error:
            self._logger.exception("Ошибка обработки задачи %s", task.id)
            if not task.is_terminal:
                task.status = "failed"
            self._results.append(
                TaskExecutionResult(task.id, "failed", handler_name, error)
            )

    async def _call_handler(self, handler: AsyncTaskHandler, task: Task) -> None:
        result = handler.handle(task)
        if not inspect.isawaitable(result):
            raise InvalidTaskHandlerError(
                "Метод handle(task) должен возвращать awaitable-объект"
            )
        await result

    def _find_handler(self, task: Task) -> AsyncTaskHandler | None:
        for handler in self._handlers:
            try:
                if handler.can_handle(task):
                    return handler
            except Exception:
                self._logger.exception(
                    "Ошибка проверки can_handle для задачи %s", task.id
                )
        return None

    def _validate_handler(self, handler: AsyncTaskHandler) -> AsyncTaskHandler:
        can_handle = getattr(handler, "can_handle", None)
        handle = getattr(handler, "handle", None)
        if (
            not isinstance(handler, AsyncTaskHandler)
            or not callable(can_handle)
            or not callable(handle)
        ):
            raise InvalidTaskHandlerError(
                "Обработчик должен реализовывать AsyncTaskHandler: "
                "can_handle(task) и async handle(task)"
            )
        return handler

    async def _enter_handler_context(self, handler: AsyncTaskHandler) -> None:
        enter_async = getattr(handler, "__aenter__", None)
        exit_async = getattr(handler, "__aexit__", None)
        if callable(enter_async) and callable(exit_async):
            await self._exit_stack.enter_async_context(handler)  # type: ignore[arg-type]
            return

        enter_sync = getattr(handler, "__enter__", None)
        exit_sync = getattr(handler, "__exit__", None)
        if callable(enter_sync) and callable(exit_sync):
            self._exit_stack.enter_context(handler)  # type: ignore[arg-type]

    async def _stop_workers(self) -> None:
        if not self._workers:
            return

        for _ in self._workers:
            await self._queue._put_stop_marker()

        await asyncio.gather(*self._workers)
        self._workers = []


class PayloadKindHandler:
    """Простой обработчик задач с маршрутизацией по payload['kind']."""

    def __init__(self, kind: str, processed_tasks: list[str] | None = None) -> None:
        self._kind = kind
        self._processed_tasks = processed_tasks if processed_tasks is not None else []

    @property
    def processed_tasks(self) -> list[str]:
        """Идентификаторы задач, обработанных этим обработчиком."""
        return list(self._processed_tasks)

    def can_handle(self, task: Task) -> bool:
        return isinstance(task.payload, dict) and task.payload.get("kind") == self._kind

    async def handle(self, task: Task) -> None:
        await asyncio.sleep(0)
        self._processed_tasks.append(task.id)
