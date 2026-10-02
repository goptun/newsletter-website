"""Leitura pública, sem token — conteúdo que já foi enviado e portanto não
é mais sensível a revisão/aprovação (ver app/storage/editions.get_latest_sent).
Consumido pela página /newsletter/ do portfolio-website (ver
docs/api-contract.md)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.dependencies import get_db
from app.api.review_html import PAGES_CSS
from app.storage import editions as editions_store

router = APIRouter()


class LatestEditionResponse(BaseModel):
    subject: str
    body: str
    sent_at: str


@router.get("/latest", response_model=LatestEditionResponse)
def latest_edition(conn=Depends(get_db)) -> LatestEditionResponse:
    edition = editions_store.get_latest_sent(conn)
    if edition is None:
        raise HTTPException(status_code=404, detail="Nenhuma edição enviada ainda")
    return LatestEditionResponse(
        subject=edition.subject or "",
        body=edition.body or "",
        sent_at=edition.sent_at or "",
    )


@router.get("/assets/pages.css", include_in_schema=False)
def pages_css() -> Response:
    """Estilo das páginas HTML de revisão e cancelamento (ver review_html.py)."""
    return Response(PAGES_CSS, media_type="text/css")
