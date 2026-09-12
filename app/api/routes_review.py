"""Revisão/aprovação de draft protegida por token secreto — ver design.md
Decisions: "Draft review/approval: a secret-link-protected endpoint, not a
full auth system" e specs/newsletter/delivery/spec.md."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_db, get_resend_client
from app.config.settings import settings
from app.delivery.pipeline import AlreadySentError, EditionNotFoundError, approve_and_send
from app.storage import editions as editions_store

router = APIRouter()


def _check_token(token: str) -> None:
    if not settings.review_secret_token:
        raise HTTPException(status_code=500, detail="REVIEW_SECRET_TOKEN não configurado")
    if token != settings.review_secret_token:
        raise HTTPException(status_code=401, detail="Token inválido")


@router.get("/review/pending")
def get_pending(token: str = Query(...), conn=Depends(get_db)):
    _check_token(token)
    edition = editions_store.get_latest_pending(conn)
    if edition is None:
        raise HTTPException(status_code=404, detail="Nenhum draft pendente")
    return edition


@router.post("/review/{edition_id}/approve")
def approve(
    edition_id: int,
    token: str = Query(...),
    conn=Depends(get_db),
    resend=Depends(get_resend_client),
):
    _check_token(token)
    try:
        return approve_and_send(conn, edition_id, resend)
    except EditionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AlreadySentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
