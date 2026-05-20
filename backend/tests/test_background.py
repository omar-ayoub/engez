import logging
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

import pytest


@asynccontextmanager
async def _fake_session_factory():
    yield MagicMock(name="fake_db_session")


@pytest.fixture(autouse=True)
def _patch_session_factory():
    with patch("app.services.background.async_session_factory", _fake_session_factory):
        yield


async def test_task_receives_db_session_and_args():
    from app.services.background import run_background

    received = {}

    async def my_task(db, x, y):
        received["db"] = db
        received["x"] = x
        received["y"] = y

    await run_background(my_task, 10, 20, task_name="test_task")
    assert received["db"] is not None
    assert received["x"] == 10
    assert received["y"] == 20


async def test_failing_task_logs_error(caplog):
    from app.services.background import run_background

    async def boom(db):
        raise ValueError("something broke")

    with caplog.at_level(logging.ERROR, logger="app.services.background"):
        await run_background(boom, task_name="exploding_task")

    assert "exploding_task" in caplog.text
    assert "something broke" in caplog.text


async def test_uses_task_name_in_log(caplog):
    from app.services.background import run_background

    async def fail_task(db):
        raise RuntimeError("oops")

    with caplog.at_level(logging.ERROR, logger="app.services.background"):
        await run_background(fail_task, task_name="custom_label")

    assert "custom_label" in caplog.text


async def test_falls_back_to_function_name(caplog):
    from app.services.background import run_background

    async def my_named_task(db):
        raise RuntimeError("oops")

    with caplog.at_level(logging.ERROR, logger="app.services.background"):
        await run_background(my_named_task)

    assert "my_named_task" in caplog.text
