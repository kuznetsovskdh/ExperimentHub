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
