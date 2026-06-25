from fastapi import FastAPI
from db import Base, engine
from routers import experiments, assignment, events, results

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ExperimentHub")
app.include_router(experiments.router)
app.include_router(assignment.router)
app.include_router(events.router)
app.include_router(results.router)

@app.get("/")
def root():
    return {"status": "ok", "service": "ExperimentHub"}
