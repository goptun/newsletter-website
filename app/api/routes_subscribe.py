"""API pública de inscrição/cancelamento — ver specs/newsletter/subscription/spec.md.

Este é o contrato que o CTA do portfolio-website vai chamar (ver
docs/api-contract.md e proposal.md: dependência cross-repo)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
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
