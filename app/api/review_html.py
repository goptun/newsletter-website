"""Renderização HTML da página de revisão diária.

Existe só pra tornar o link do e-mail de notificação (ver
app/delivery/notify.py) clicável num navegador com segurança: os botões
fazem POST de verdade (via <form>), não é um link GET de um clique — um
GET de aprovação seria acionado por scanners de segurança de e-mail (ex.:
o link-prefetch do Gmail) antes do dono sequer abrir a mensagem, furando
a garantia de "só envia com aprovação humana explícita" (ver
specs/newsletter/delivery/spec.md, Requirement: Draft requires approval
before send).

As actions dos formulários usam caminho relativo sem barra inicial
("{id}/approve?token=...") de propósito: a página é servida atrás do
proxy Nginx em /api/newsletter/review/page (ver infra/nginx/), e o
FastAPI aqui dentro não enxerga esse prefixo. Uma action com barra
inicial resolveria contra a raiz do domínio e perderia o prefixo; sem
barra, o navegador resolve relativo ao diretório da própria página
(.../api/newsletter/review/), preservando o prefixo automaticamente."""

from __future__ import annotations

from html import escape

from app.storage.editions import Edition

_STYLE = """
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 40rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.6;
         color: #111110; background: #fdfdfc; }
  .meta { color: #6b6a67; font-size: 0.85rem; margin-bottom: 1.5rem; }
  .subject { font-size: 1.15rem; font-weight: 600; margin-bottom: 1.25rem; }
  .body p { margin: 0 0 1rem; }
  .actions { margin-top: 2rem; display: flex; gap: 0.75rem; flex-wrap: wrap; }
  button { font-size: 1rem; padding: 0.65rem 1.3rem; border-radius: 0.375rem;
           border: 1px solid #111110; cursor: pointer; }
  .approve { background: #111110; color: #fdfdfc; }
  .reject { background: #fdfdfc; color: #111110; }
"""


def _page(title: str, body_html: str) -> str:
    return (
        "<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head>"
        f"<body>{body_html}</body></html>"
    )


def render_pending_page(edition: Edition, token: str) -> str:
    paragraphs = "".join(f"<p>{escape(p)}</p>" for p in (edition.body or "").split("\n\n"))
    encoded_token = escape(token)
    body_html = f"""
      <div class="meta">Edição de {escape(edition.edition_date)} — aguardando revisão</div>
      <div class="subject">{escape(edition.subject or "")}</div>
      <div class="body">{paragraphs}</div>
      <div class="actions">
        <form method="post" action="{edition.id}/approve?token={encoded_token}">
          <button class="approve" type="submit">Aprovar e enviar</button>
        </form>
        <form method="post" action="{edition.id}/reject?token={encoded_token}">
          <button class="reject" type="submit">Rejeitar</button>
        </form>
      </div>
    """
    return _page(f"Revisar edição — {edition.edition_date}", body_html)


def render_no_pending_page() -> str:
    return _page("Nenhum draft pendente", "<p>Nenhum draft aguardando revisão no momento.</p>")


def render_confirmation_page(message: str) -> str:
    return _page(message, f"<p>{escape(message)}</p>")
