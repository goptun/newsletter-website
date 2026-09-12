"""API pública de inscrição/cancelamento — ver specs/newsletter/subscription/spec.md.

Este é o contrato que o CTA do portfolio-website vai chamar (ver
docs/api-contract.md e proposal.md: dependência cross-repo)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.api.dependencies import get_db
from app.storage import subscribers as subscribers_store

router = APIRouter()


class SubscribeRequest(BaseModel):
    email: str


class SubscribeResponse(BaseModel):
    status: str


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe(payload: SubscribeRequest, conn=Depends(get_db)) -> SubscribeResponse:
    try:
        subscribers_store.subscribe(conn, payload.email)
    except subscribers_store.InvalidEmailError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SubscribeResponse(status="subscribed")


@router.post("/unsubscribe", response_model=SubscribeResponse)
def unsubscribe(payload: SubscribeRequest, conn=Depends(get_db)) -> SubscribeResponse:
    subscribers_store.unsubscribe(conn, payload.email)
    return SubscribeResponse(status="unsubscribed")


@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe_via_link(email: str = Query(...), conn=Depends(get_db)) -> HTMLResponse:
    """Versão GET, pra funcionar como link clicável no rodapé do e-mail
    (ver app/delivery/email_template.py) — cancelar a própria inscrição é
    uma ação de baixo risco (o pior caso é alguém cancelar a inscrição de
    outra pessoa sabendo o e-mail dela, o mesmo modelo de confiança que
    praticamente toda newsletter usa), diferente de aprovar/enviar pra
    todo mundo, que exige POST (ver app/api/routes_review.py)."""
    subscribers_store.unsubscribe(conn, email)
    return HTMLResponse(
        "<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        "<title>Inscrição cancelada</title></head>"
        "<body style=\"font-family:-apple-system,sans-serif;max-width:32rem;margin:3rem auto;padding:0 1rem;\">"
        "<p>Sua inscrição foi cancelada. Você não vai mais receber a newsletter.</p>"
        "</body></html>"
    )
