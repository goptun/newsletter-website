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

# Folha de estilo das páginas HTML deste serviço (revisão e cancelamento),
# servida por GET /assets/pages.css (ver routes_public.py) e linkada, em vez
# de um <style> inline, porque a CSP do domínio (style-src 'self', sem
# 'unsafe-inline') bloqueia estilo inline. Mesma paleta e fontes do
# portfolio-website (src/styles/global.css; as fontes vêm de /fonts/ dele).
PAGES_CSS = """
:root {
  color-scheme: light dark;
  --bg: #F8FAF9; --surface: #FFFFFF; --border: #DDE3E8; --text: #0B0E13;
  --text-2: #4A5563; --text-3: #626D7A; --accent: #047857; --accent-bg: #E3F5EE;
  --glow: rgba(52, 211, 153, 0.12); --dots: #E3E8EC;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme='light']) {
    --bg: #0B0E13; --surface: #12161D; --border: #28303A; --text: #ECF0F4;
    --text-2: #96A0AC; --text-3: #7D8794; --accent: #34D399; --accent-bg: #102822;
    --glow: rgba(18, 52, 44, 0.9); --dots: #181E26;
  }
}
:root[data-theme='dark'] {
  color-scheme: dark;
  --bg: #0B0E13; --surface: #12161D; --border: #28303A; --text: #ECF0F4;
  --text-2: #96A0AC; --text-3: #7D8794; --accent: #34D399; --accent-bg: #102822;
  --glow: rgba(18, 52, 44, 0.9); --dots: #181E26;
}
:root[data-theme='light'] { color-scheme: light; }
body {
  font-family: 'Noto Sans', system-ui, sans-serif;
  max-width: 40rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.6;
  color: var(--text);
  background-color: var(--bg);
  background-image:
    radial-gradient(ellipse 60% 80% at 95% 0%, var(--glow), transparent 70%),
    radial-gradient(circle, var(--dots) 1.5px, transparent 1.5px);
  background-size: 100% 100%, 36px 36px;
  background-attachment: fixed;
}
@media (hover: none) { body { background-attachment: scroll; } }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.meta { font-family: 'JetBrains Mono', ui-monospace, monospace; color: var(--text-3);
        font-size: 0.85rem; margin-bottom: 1.5rem; }
.subject { font-size: 1.15rem; font-weight: 700; margin-bottom: 1.25rem; }
.body { background: var(--surface); border: 1px solid var(--border); border-radius: 0.625rem;
        padding: 1.25rem 1.5rem; }
.body p { margin: 0 0 1rem; }
.body p:last-child { margin-bottom: 0; }
.actions { margin-top: 2rem; display: flex; gap: 0.75rem; flex-wrap: wrap; }
button { font: inherit; font-weight: 700; padding: 0.65rem 1.3rem; border-radius: 0.625rem;
         cursor: pointer; }
.approve { background: var(--accent); color: var(--bg); border: 1px solid var(--accent); }
.reject { background: transparent; color: var(--text); border: 1px solid var(--border); }
"""


def render_page(title: str, body_html: str, css_href: str) -> str:
    """`css_href` é relativo à URL da própria página (mesmo motivo das
    actions dos formulários, ver docstring do módulo): o prefixo
    /api/newsletter/ do Nginx não é visível aqui dentro."""
    return (
        "<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title>"
        # Ícones servidos pelo portfolio-website (mesmo domínio).
        '<link rel="icon" href="/favicon.ico" sizes="48x48">'
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg">'
        '<script src="/theme-init.js"></script>'
        '<link rel="stylesheet" href="/fonts/fonts.css">'
        f'<link rel="stylesheet" href="{escape(css_href)}">'
        f"</head><body>{body_html}</body></html>"
    )


# Caminhos relativos até a raiz do serviço: .../review/page fica um nível
# abaixo dela; as confirmações (POST .../review/{id}/approve|reject), dois.
_REVIEW_CSS_HREF = "../assets/pages.css"
_CONFIRMATION_CSS_HREF = "../../assets/pages.css"


def _page(title: str, body_html: str, css_href: str = _REVIEW_CSS_HREF) -> str:
    return render_page(title, body_html, css_href)


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
    return _page(message, f"<p>{escape(message)}</p>", _CONFIRMATION_CSS_HREF)
