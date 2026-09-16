"""Renderização HTML da edição enviada por e-mail.

O texto salvo em editions.body (a Curiosidade do dia + as notícias,
separadas por linha em branco — ver app/generation/pipeline.py) ia direto
pro campo "html" do envio do Resend sem nenhuma marcação. HTML ignora
quebras de linha soltas, então tudo chegava junto, sem separação entre
parágrafos, no e-mail de verdade. Este módulo transforma esse texto em
HTML com estilos inline (padrão em e-mail — muitos clientes ignoram
`<style>` no `<head>`) e acrescenta o link de cancelamento de inscrição
no rodapé, que antes só existia via chamada direta à API (ver
specs/newsletter/subscription/spec.md, Requirement: Unsubscribe)."""

from __future__ import annotations

from html import escape
from urllib.parse import quote

UNSUBSCRIBE_URL_BASE = "https://matheusramos.dev/api/newsletter/unsubscribe"

_CONTAINER_STYLE = (
    "max-width:600px;margin:0 auto;padding:24px 16px;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
    "color:#111110;line-height:1.6;"
)
_CURIOSIDADE_STYLE = "font-size:13px;color:#6b6a67;font-style:italic;margin:0 0 22px;"
_PARAGRAPH_STYLE = "margin:0 0 18px;font-size:15px;"
_FOOTER_STYLE = "font-size:12px;color:#9a9a96;margin:0;"
_LINK_STYLE = "color:#9a9a96;"


def unsubscribe_url_for(email: str) -> str:
    return f"{UNSUBSCRIBE_URL_BASE}?email={quote(email)}"


def render_edition_text(body: str, unsubscribe_email: str) -> str:
    """Alternativa em texto puro do mesmo conteúdo de render_edition_html —
    e-mails sem multipart/alternative (só HTML) são um sinal usado por
    filtros de spam."""
    unsubscribe_url = unsubscribe_url_for(unsubscribe_email)
    return (
        f"{body}\n\n"
        f"--\nVocê está recebendo porque assinou em matheusramos.dev. "
        f"Cancelar inscrição: {unsubscribe_url}"
    )


def _render_news_paragraph(paragraph: str) -> str:
    # Destaca a frase-manchete antes dos dois-pontos em negrito, o resto
    # em texto normal.
    if ": " in paragraph:
        lead, rest = paragraph.split(": ", 1)
        text = f"<strong>{escape(lead)}:</strong> {escape(rest)}"
    else:
        text = escape(paragraph)
    return f'<p style="{_PARAGRAPH_STYLE}">{text}</p>'


def render_edition_html(body: str, unsubscribe_email: str) -> str:
    """`body` é o texto puro de editions.body: primeiro parágrafo é a
    Curiosidade do dia, os demais são as notícias."""
    paragraphs = [p.strip() for p in (body or "").split("\n\n") if p.strip()]
    if not paragraphs:
        return ""

    curiosidade, *news_paragraphs = paragraphs
    news_html = "".join(_render_news_paragraph(p) for p in news_paragraphs)
    unsubscribe_url = unsubscribe_url_for(unsubscribe_email)

    return (
        f'<div style="{_CONTAINER_STYLE}">'
        f'<p style="{_CURIOSIDADE_STYLE}">{escape(curiosidade)}</p>'
        f"{news_html}"
        f'<hr style="border:none;border-top:1px solid #e6e4e0;margin:28px 0 16px;">'
        f'<p style="{_FOOTER_STYLE}">Você está recebendo porque assinou em '
        f'matheusramos.dev. <a href="{escape(unsubscribe_url)}" style="{_LINK_STYLE}">'
        "Cancelar inscrição</a></p>"
        "</div>"
    )
