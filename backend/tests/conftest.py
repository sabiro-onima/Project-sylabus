import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop(request):
    """Session-wide event loop — один loop на все тесты."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    try:
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.wait(pending, timeout=10))
    except Exception:
        pass
    try:
        loop.run_until_complete(asyncio.sleep(0.2))
    except Exception:
        pass
    finally:
        loop.close()
