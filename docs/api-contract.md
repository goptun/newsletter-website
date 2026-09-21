# Contrato da API de inscrição

Contrato estável para o CTA de assinatura do `portfolio-website` chamar —
ver `openspec/changes/daily-newsletter-system/proposal.md` (dependência
cross-repo) e `design.md` ("Cross-repo integration boundary").

Servido em produção via `https://matheusramos.dev/api/newsletter/...`
(Nginx faz proxy pra `newsletter_api`, stripando o prefixo — ver
`infra/nginx/newsletter-location.conf` e `DEPLOY.md`). Em dev local, a API
roda direto em `http://127.0.0.1:8001/...` (sem o prefixo).

## `POST /api/newsletter/subscribe`

Inscreve um e-mail na newsletter. Idempotente: reenviar o mesmo e-mail já
ativo é um no-op que ainda responde 200.

**Request**

```json
{ "email": "leitor@example.com" }
```

**Response — 200 OK**

```json
{ "status": "subscribed" }
```

**Response — 422 Unprocessable Entity** (e-mail malformado, nada é
persistido)

```json
{ "detail": "E-mail inválido: 'nao-e-um-email'" }
```

## `POST /api/newsletter/unsubscribe`

Cancela a inscrição de um e-mail. Idempotente: e-mail desconhecido ou já
cancelado também responde 200 (a intenção do chamador — "esse e-mail não
deve mais receber a newsletter" — já está satisfeita).

**Request**

```json
{ "email": "leitor@example.com" }
```

**Response — 200 OK**

```json
{ "status": "unsubscribed" }
```

## `GET /api/newsletter/latest`

Devolve a edição mais recente que já foi **enviada** (nunca um draft
pendente de revisão — esse ainda pode ser rejeitado ou não passou pela
aprovação do dono). Usado pela página `/newsletter/` do portfolio-website
pra mostrar a última edição.

**Response — 200 OK**

```json
{
  "subject": "Segurança em foco: npm malicioso e falha no Codex",
  "body": "Curiosidade do dia: Em 21 de setembro de 1995, ...\n\nTítulo curto: desenvolvimento da notícia. As informações são do site X.\n\n...",
  "sent_at": "2026-09-12 17:10:43"
}
```

`body` é texto puro com parágrafos separados por linha em branco (mesmo
formato salvo internamente) — o primeiro parágrafo é a "Curiosidade do
dia", os demais são as notícias. Cabe ao consumidor renderizar (ver
`app/delivery/email_template.py` pra um exemplo de como isso é feito no
e-mail).

**Response — 404 Not Found** (nenhuma edição foi enviada ainda)

```json
{ "detail": "Nenhuma edição enviada ainda" }
```

## Exemplo (fetch, do lado do portfolio-website)

```js
async function subscribe(email) {
  const res = await fetch("/api/newsletter/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const { detail } = await res.json();
    throw new Error(detail || "Falha ao assinar");
  }
  return res.json();
}
```

Caminho relativo (`/api/newsletter/subscribe`), sem CORS: o Nginx do
`matheusramos.dev` serve o portfolio e faz proxy da API sob o mesmo
domínio, então a chamada é same-origin — ver `design.md` Decisions:
"Cross-repo integration boundary".
