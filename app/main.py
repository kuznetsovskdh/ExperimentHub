from fastapi import FastAPI
from db import Base, engine
from routers import experiments, assignment

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ExperimentHub")
app.include_router(experiments.router)
app.include_router(assignment.router)

@app.get("/")
def root():
    return {"status": "ok", "service": "ExperimentHub"}
