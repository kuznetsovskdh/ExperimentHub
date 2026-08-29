from fastapi import FastAPI
from sqlalchemy import text
from db import Base, engine
from routers import (
    experiments, assignment, events, results, quasi_experimental, stats_tools
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ExperimentHub",
    description=(
        "Продуктово-агностичная платформа A/B-тестирования и quasi-experimental "
        "анализа. Единица эксперимента (entity_id) и метрика передаются как "
        "абстрактные параметры, поэтому один сервис обслуживает и AB-тест на "
        "пользователях, и DiD-оценку акции на SKU."
    ),
    version="1.0.0",
)

app.include_router(experiments.router)
app.include_router(assignment.router)
app.include_router(events.router)
app.include_router(results.router)
app.include_router(quasi_experimental.router)
app.include_router(stats_tools.router)


@app.get("/")
def root():
    """
    Корень сервиса.

    Отдаёт не только статус, но и куда идти дальше: человек, открывший этот
    адрес в браузере, иначе упирается в голый JSON и не понимает, что делать.
    """
    return {
        "status": "ok",
        "service": "ExperimentHub",
        "links": {
            "документация_api": "/docs",
            "интерфейс": "http://localhost:3002",
            "проверка_живости": "/health",
        },
        "быстрый_старт": {
            "создать_эксперимент": "POST /experiments/",
            "получить_вариант": "GET /experiments/{id}/assignment?entity_id=X",
            "отправить_метрику": "POST /experiments/{id}/events",
            "результаты": "GET /experiments/{id}/results?metric_name=X",
        },
    }


@app.get("/health")
def health():
    """Проверка живости вместе с доступностью БД — используется healthcheck'ом."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception as e:
        return {"status": "degraded", "database": f"unavailable: {type(e).__name__}"}
