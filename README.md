# newsletter-website

Backend (Python/FastAPI) de uma newsletter diária de tecnologia:
coleta notícias reais via RSS, gera uma edição com um LLM (via 9Router),
espera aprovação manual do dono e só então envia por e-mail aos
assinantes via Resend.

Modelada na a reference newsletter, mas sem a parte patrocinada e
sem comentário editorial por notícia — ver
`openspec/changes/archive/2026-09-12-daily-newsletter-system/proposal.md`
para o contexto completo da decisão de produto.

## Como funciona

1. **Coleta** (`app/news/`): busca itens recentes em feeds RSS de fontes
   confiáveis (TechCrunch, The Verge, Ars Technica, The Register,
   BleepingComputer, 9to5Google, 404 Media) e seleciona os mais
   relevantes. Nenhum conteúdo é inventado — se uma fonte cai, ela é
   simplesmente ignorada.
2. **Geração** (`app/generation/`): um scheduler in-process
   (APScheduler, `app/scheduler.py`) dispara todo dia às 06:00 a geração
   da edição via LLM (endpoint OpenAI-compatible do 9Router), seguindo a
   estrutura de referência: assunto com 2-3 manchetes, abertura
   "Curiosidade do dia", um parágrafo por notícia terminando com a fonte.
   Um filtro de relevância via LLM descarta conteúdo fora do tema. O
   resultado fica como **draft**, nunca enviado automaticamente.
3. **Revisão** (`app/api/routes_review.py`): o dono recebe uma
   notificação por e-mail com um link protegido por token secreto
   (`REVIEW_SECRET_TOKEN`) para aprovar ou rejeitar o draft — uma página
   HTML com botões, sem sistema de login completo.
4. **Envio** (`app/delivery/`): ao aprovar, a edição é enviada a todos os
   assinantes ativos via Resend, a partir de `newsletter@matheusramos.dev`.
5. **Assinatura** (`app/api/routes_subscribe.py`): API pública de
   inscrição/cancelamento, pensada para ser chamada pelo CTA de
   assinatura do `portfolio-website` (repositório separado) — contrato
   documentado em `docs/api-contract.md`.

## Stack

- FastAPI + Uvicorn
- SQLite (armazenamento de assinantes e edições)
- APScheduler (job diário in-process, sem cron externo)
- feedparser (coleta RSS)
- Resend (envio de e-mail transacional)
- LLM via 9Router (gateway OpenAI-compatible já usado por
  `rag-knowledge-assistant`, reaproveitado aqui — não é substituído por
  outro provedor)

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# preencha pelo menos LLM_BASE_URL/LLM_MODEL, RESEND_API_KEY e
# REVIEW_SECRET_TOKEN pra geração/envio funcionarem de verdade

python scripts/run_api.py
# API sobe em http://127.0.0.1:8001 (com --reload)
```

Disparar a geração da edição do dia manualmente, sem esperar o
scheduler:

```bash
python scripts/generate_now.py
```

## Testes

```bash
pytest
```

## Configuração

Variáveis de ambiente (ver `.env.example` para a lista completa e
comentada):

| Variável | Descrição |
| --- | --- |
| `DB_PATH` | Caminho do arquivo SQLite |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | Endpoint do 9Router e modelo do combo em uso |
| `GENERATION_MAX_TOKENS`, `GENERATION_TEMPERATURE` | Parâmetros de geração |
| `NEWS_MAX_ITEMS` | Número máximo de notícias por edição |
| `RESEND_API_KEY`, `NEWSLETTER_FROM_ADDRESS` | Envio via Resend |
| `NEWSLETTER_OWNER_EMAIL`, `REVIEW_BASE_URL` | Notificação de "draft pronto para revisão" |
| `REVIEW_SECRET_TOKEN` | Token que protege os endpoints de aprovação/rejeição |

## Estrutura do projeto

```
app/
  api/         # rotas FastAPI (subscribe, review, latest edition) e entrypoint
  config/      # settings via variáveis de ambiente
  delivery/    # template de e-mail, envio via Resend, notificações ao dono
  generation/  # cliente LLM, prompts, pipeline de geração, filtro de relevância
  news/        # coleta RSS e seleção de notícias
  storage/     # acesso a SQLite (assinantes e edições)
  scheduler.py # job diário in-process (APScheduler)
scripts/       # entrypoints manuais (subir API, gerar edição sob demanda)
tests/         # suíte pytest
docs/          # contrato de API pro portfolio-website consumir
openspec/      # specs e histórico de mudanças (OpenSpec)
docker/        # Dockerfile e docker-compose de deploy
infra/nginx/   # snippet de proxy reverso a ser mesclado no domínio principal
```

## Deploy

Ver `DEPLOY.md` — roda como container Docker isolado na mesma VPS de
`portfolio-website` e `rag-knowledge-assistant`, reusando o 9Router já em
execução lá.

## Integração cross-repo

O botão de assinatura em si vive no `portfolio-website` (repositório
separado). O contrato estável que ele consome está em
`docs/api-contract.md` (`/subscribe`, `/unsubscribe`, `/latest`).
