# Deploy

`newsletter_api` roda como um serviço Docker isolado na mesma VPS Oracle
que hospeda `portfolio-website` e `rag-knowledge-assistant` (ver
`openspec/changes/daily-newsletter-system/design.md`). Reusa o 9Router já
em execução no stack do `rag-knowledge-assistant` — este repositório não
sobe outro 9Router.

- **Host**: `<VPS_HOST_IP>` (Ubuntu 24.04, ARM) — mesma VPS documentada em
  `../portfolio-website/DEPLOY.md`.
- **Serviço**: container `newsletter_api`, escutando só em
  `127.0.0.1:8001` (não exposto diretamente à internet).
- **Dados**: SQLite em um volume Docker nomeado (`newsletter_data`,
  montado em `/app/data`) — assinantes e edições ficam nesse volume.
- **Nginx**: proxied via `/api/newsletter/` — ver seção abaixo.

## Deploy inicial / atualização

```bash
export DEPLOY_HOST=ubuntu@<VPS_HOST_IP>
export DEPLOY_KEY=~/Desktop/ssh-key-2026-09-09-oracle.key

# 1. Envia o código pra VPS (ou faz git pull lá, se o repo já estiver clonado)
rsync -az --exclude .venv --exclude data -e "ssh -i $DEPLOY_KEY" ./ "$DEPLOY_HOST:~/newsletter-website/"

# 2. Garante o .env configurado na VPS (LLM_BASE_URL já deve apontar pro
#    9Router existente, ex.: http://<TAILSCALE_9ROUTER_IP>:20128/v1 — ver
#    .env.example). RESEND_API_KEY e REVIEW_SECRET_TOKEN são obrigatórios
#    pra geração/envio funcionarem de verdade.
ssh -i "$DEPLOY_KEY" "$DEPLOY_HOST" "test -f ~/newsletter-website/.env || echo 'FALTA CRIAR .env NA VPS'"

# 3. Builda e sobe (ou atualiza) o container
ssh -i "$DEPLOY_KEY" "$DEPLOY_HOST" \
  "cd ~/newsletter-website && docker compose -f docker/docker-compose.yml up -d --build"
```

## Rollback

Isolado por natureza: o rollback é simplesmente parar/remover só este
stack, sem tocar nos demais serviços da VPS.

```bash
ssh -i "$DEPLOY_KEY" "$DEPLOY_HOST" \
  "cd ~/newsletter-website && docker compose -f docker/docker-compose.yml down"
```

Pra voltar a uma versão anterior do código: `git checkout <commit-anterior>`
na VPS (ou reenviar via rsync uma cópia antiga) e repetir o passo 3 acima.
O volume `newsletter_data` (assinantes/edições) não é afetado por isso.

## Nginx

O bloco de proxy para `/api/newsletter/` vive em
`infra/nginx/newsletter-location.conf` neste repositório, mas **o arquivo
de config real do domínio `matheusramos.dev` está no repositório
`portfolio-website`** (`portfolio-website/infra/nginx/matheusramos.dev.conf`),
que é quem efetivamente é copiado pra VPS. Passos:

1. Copie o conteúdo de `infra/nginx/newsletter-location.conf` (deste repo)
   pra dentro do bloco `server { listen 443 ssl; server_name
   matheusramos.dev; ... }` em
   `portfolio-website/infra/nginx/matheusramos.dev.conf`.
2. Siga os passos de "Updating the Nginx config" já documentados em
   `portfolio-website/DEPLOY.md` (que já inclui `nginx -t` antes do
   reload — **nunca pule essa checagem**: a VPS também serve
   `rag.matheusramos.dev` e o site principal, e uma config quebrada
   derruba os três).

Isso mantém a config do domínio centralizada em um único lugar
(`portfolio-website`), com este repositório só documentando o snippet que
precisa ser mesclado lá.
