from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine

from app.api import auth, parts, stations, trace_events, metrics, ai, user

# Crear tablas al inicio (para el proyecto escolar está bien; en algo serio usar Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Trace API")

app.include_router(auth.router)
app.include_router(parts.router)
app.include_router(stations.router)
app.include_router(trace_events.router)
app.include_router(metrics.router)
app.include_router(ai.router)
app.include_router(user.router)


@app.get("/")
def root():
    return {"message": "Trace API funcionando"}
