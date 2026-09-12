"""Entrypoint da API — monta o DB real e registra o job diário de geração
no startup (ver app/api/dependencies.py e app/scheduler.py).

Rodar:
    python scripts/run_api.py
    # ou diretamente:
    uvicorn app.api.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import dependencies
from app.api.routes_review import router as review_router
from app.api.routes_subscribe import router as subscribe_router
from app.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    dependencies.ensure_schema()
    app.state.scheduler = start_scheduler()
    yield
    app.state.scheduler.shutdown(wait=False)


app = FastAPI(title="newsletter-website", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(subscribe_router)
app.include_router(review_router)
