"""Configuração central do projeto via variáveis de ambiente.

Segue o mesmo padrão de rag-knowledge-assistant/app/config/settings.py:
defaults vazios para segredos, validados no ponto de uso (não no import),
pra permitir subir a API sem tudo configurado ainda (ver tasks.md 1.3)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco de dados
    db_path: str = "data/newsletter.db"

    # LLM — único provedor suportado é o 9Router (ver proposal.md: "Não
    # substitua o 9Router por outra API ou serviço de LLM sem necessidade")
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    # O combo do 9Router em produção (@cf/openai/gpt-oss-120b) é um modelo de
    # raciocínio: gasta uma quantidade variável de tokens "pensando" antes da
    # resposta final, e esse gasto conta pro mesmo orçamento de max_tokens.
    # Medido em produção: ~1750 tokens só de raciocínio pra a "Curiosidade do
    # dia" (a tarefa mais aberta); um valor baixo corta a resposta antes do
    # conteúdo final, deixando o campo vazio (ver DEPLOY.md "Troubleshooting").
    generation_max_tokens: int = 4096
    generation_temperature: float = 0.4

    # Notícias
    news_max_items: int = 6

    # Envio (Resend)
    resend_api_key: str = ""
    newsletter_from_address: str = "newsletter@matheusramos.dev"

    # Notificação de "draft pronto para revisão"
    newsletter_owner_email: str = ""
    review_base_url: str = "http://127.0.0.1:8001"

    # Swagger UI / OpenAPI públicos (/docs, /redoc, /openapi.json): desligados
    # por padrão — em produção só revelariam a superfície da API (rotas de
    # revisão inclusive). Ligue com ENABLE_DOCS=true no .env pra desenvolver.
    enable_docs: bool = False

    # Revisão/aprovação do draft — protegida por token secreto (ver
    # design.md Decision: "secret-link-protected endpoint")
    review_secret_token: str = ""


settings = Settings()
