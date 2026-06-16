"""
fix4.py — убирает 2 ERROR при teardown (Event loop is closed).

Запуск из папки проекта:
  docker compose run --rm --no-deps -v "${PWD}/fix4.py:/app/fix4.py" backend python fix4.py
"""
import pathlib

BASE = pathlib.Path("/app")

# ── conftest.py ──────────────────────────────────────────────────────────────
(BASE / "tests/conftest.py").write_text('''\
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
    # Критично: даём asyncpg обработать отложенные задачи ДО закрытия loop
    try:
        loop.run_until_complete(asyncio.sleep(0.2))
    except Exception:
        pass
    finally:
        loop.close()
''')
print("OK: conftest.py")

# ── test_api_full.py — teardown _init_test_db ────────────────────────────────
p = BASE / "tests/test_api_full.py"
text = p.read_text()

MARKERS = [
    # вариант A — оригинальный
    (
        "    await _test_engine.dispose()\n"
        "    try:\n"
        "        admin_engine2 = create_async_engine(_PROD_URL, echo=False)\n"
        "        await admin_engine2.dispose()\n"
        "    except Exception:\n"
        "        pass",
        "    await _test_engine.dispose(close=True)\n"
        "    import asyncio as _asyncio\n"
        "    await _asyncio.sleep(0.2)"
    ),
    # вариант B — после частичного патча
    (
        "    await _test_engine.dispose()\n",
        "    await _test_engine.dispose(close=True)\n"
        "    import asyncio as _asyncio\n"
        "    await _asyncio.sleep(0.2)\n"
    ),
]

patched = False
for old, new in MARKERS:
    if old in text:
        text = text.replace(old, new)
        p.write_text(text)
        print("OK: _init_test_db dispose исправлен")
        patched = True
        break

if not patched:
    if "dispose(close=True)" in text:
        print("SKIP: уже исправлено")
    else:
        print("WARN: якорь не найден — проверь файл вручную")

print("\nГотово! Запусти тесты:")
print("  docker compose run --rm backend python -m pytest tests/test_api_full.py -v")
