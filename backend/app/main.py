from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cases, evidence, imports, reports, reviews
from app.config import validate_configuration
from app.db import initialize_database
from app.security.auth import Actor, current_actor


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_configuration()
    initialize_database()
    yield


app = FastAPI(
    title="LossLens CaseOps",
    description="Restricted synthetic inventory reconciliation and case documentation workspace.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(imports.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "data": "synthetic"}


@app.get("/api/session")
def session(actor: Actor = Depends(current_actor)) -> dict[str, str]:
    return {"role": actor.role, "actor_id": actor.actor_id}