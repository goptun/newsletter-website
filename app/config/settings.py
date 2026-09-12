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
    generation_max_tokens: int = 2048
    generation_temperature: float = 0.4

    # Notícias
    news_max_items: int = 6

    # Envio (Resend)
    resend_api_key: str = ""
    newsletter_from_address: str = "newsletter@matheusramos.dev"

    # Notificação de "draft pronto para revisão"
    newsletter_owner_email: str = ""
    review_base_url: str = "http://127.0.0.1:8001"

    # Revisão/aprovação do draft — protegida por token secreto (ver
    # design.md Decision: "secret-link-protected endpoint")
    review_secret_token: str = ""


settings = Settings()
