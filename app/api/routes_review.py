"""Revisão/aprovação de draft protegida por token secreto — ver design.md
Decisions: "Draft review/approval: a secret-link-protected endpoint, not a
full auth system" e specs/newsletter/delivery/spec.md.

Duas superfícies pro mesmo fluxo: uma API JSON (pra automação/curl, ver
docs/api-contract.md) e uma página HTML com botões (pra clicar direto no
e-mail de notificação — ver app/api/review_html.py pro porquê dos botões
fazerem POST em vez de um link GET de um clique)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.api import review_html
from app.api.dependencies import get_db, get_resend_client
from app.config.settings import settings
from app.delivery.pipeline import (
    AlreadySentError,
    EditionNotFoundError,
    InvalidEditionStateError,
    approve_and_send,
    reject_draft,
)
from app.storage import editions as editions_store

router = APIRouter()


def _check_token(token: str) -> None:
    if not settings.review_secret_token:
        raise HTTPException(status_code=500, detail="REVIEW_SECRET_TOKEN não configurado")
    if token != settings.review_secret_token:
        raise HTTPException(status_code=401, detail="Token inválido")


def _wants_html(request: Request) -> bool:
    """Formulários HTML enviados por um navegador de verdade pedem
    text/html no Accept; chamadas via curl/httpx (a API JSON, os testes)
    não mandam esse valor por padrão — usado pra decidir se a resposta de
    approve/reject é a página de confirmação ou o JSON cru."""
    return "text/html" in request.headers.get("accept", "")


@router.get("/review/pending")
def get_pending(token: str = Query(...), conn=Depends(get_db)):
    _check_token(token)
    edition = editions_store.get_latest_pending(conn)
    if edition is None:
        raise HTTPException(status_code=404, detail="Nenhum draft pendente")
    return edition


@router.get("/review/page", response_class=HTMLResponse)
def review_page(token: str = Query(...), conn=Depends(get_db)):
    _check_token(token)
    edition = editions_store.get_latest_pending(conn)
    if edition is None:
        return HTMLResponse(review_html.render_no_pending_page())
    return HTMLResponse(review_html.render_pending_page(edition, token))


@router.post("/review/{edition_id}/approve")
def approve(
    edition_id: int,
    request: Request,
    token: str = Query(...),
    conn=Depends(get_db),
    resend=Depends(get_resend_client),
):
    _check_token(token)
    try:
        edition = approve_and_send(conn, edition_id, resend)
    except EditionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AlreadySentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidEditionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if _wants_html(request):
        return HTMLResponse(
            review_html.render_confirmation_page(f"Edição {edition.edition_date} enviada!")
        )
    return edition


@router.post("/review/{edition_id}/reject")
def reject(
    edition_id: int,
    request: Request,
    token: str = Query(...),
    conn=Depends(get_db),
):
    _check_token(token)
    try:
        edition = reject_draft(conn, edition_id)
    except EditionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AlreadySentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidEditionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if _wants_html(request):
        return HTMLResponse(
            review_html.render_confirmation_page(f"Edição {edition.edition_date} rejeitada.")
        )
    return edition
