"""
Общая настройка для всех тестов.

app/ — это --app-dir сервиса, поэтому модули импортируются как top-level
(from stats.frequentist import ...). Добавляем его в sys.path здесь один раз,
чтобы отдельные тесты этого не делали.
"""
import os
import sys

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Базовый URL живого сервиса для e2e-тестов (внутри контейнера — сам себя).
EH_BASE = os.environ.get("EH_TEST_BASE_URL", "http://localhost:8000")


# Тестовые данные не должны накапливаться в рабочей базе: за десяток прогонов
# список экспериментов забивается сотнями пустых записей, и интерфейс
# становится нечитаемым. Имена тестовых экспериментов имеют префиксы
# test-/e2e-, поэтому их можно снести точечно, не трогая настоящие.
TEST_NAME_PATTERN = "^(test-|e2e-|uitest-|ui-selftest|manual-check|bad$|dup$|one$)"


def _purge_test_experiments():
    try:
        from db import SessionLocal
        from sqlalchemy import text
    except Exception:
        return

    session = SessionLocal()
    try:
        ids = [
            row[0]
            for row in session.execute(
                text("SELECT id FROM experiments WHERE name ~ :p"),
                {"p": TEST_NAME_PATTERN},
            )
        ]
        if not ids:
            return
        for table in ("results", "events", "assignments", "variants"):
            session.execute(
                text(f"DELETE FROM {table} WHERE experiment_id = ANY(:ids)"),
                {"ids": ids},
            )
        session.execute(
            text("DELETE FROM experiments WHERE id = ANY(:ids)"), {"ids": ids}
        )
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Убрать за собой после прогона — независимо от того, прошли тесты или нет."""
    _purge_test_experiments()
