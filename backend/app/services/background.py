import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.database import async_session_factory

logger = logging.getLogger(__name__)


async def run_background(
    task_fn: Callable[..., Awaitable[Any]],
    *args: Any,
    task_name: str = "",
) -> None:
    name = task_name or task_fn.__name__
    try:
        async with async_session_factory() as db:
            await task_fn(db, *args)
    except Exception:
        logger.exception("Background task '%s' failed", name)
