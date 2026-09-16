"""Cliente do 9Router — único provedor de LLM deste projeto (ver
proposal.md: "Não substitua o 9Router por outra API ou serviço de LLM sem
necessidade").

Adaptado de OpenAICompatibleLLMClient em
rag-knowledge-assistant/app/generation/llm_client.py (mesmo endpoint
OpenAI-compatible, mesmo 9Router), mas sem streaming: aqui geramos um
documento completo (a edição do dia) de uma vez, não uma resposta de chat
exibida token a token pra um usuário."""

from __future__ import annotations


class LLMNotConfiguredError(RuntimeError):
    pass


class NineRouterClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.4,
    ):
        if not base_url:
            raise LLMNotConfiguredError(
                "LLM_BASE_URL não configurada. Defina no .env apontando pro 9Router "
                "(ver .env.example pro formato)."
            )
        if not model:
            raise LLMNotConfiguredError(
                "LLM_MODEL não configurado — veja o combo exposto no dashboard do 9Router."
            )

        from openai import OpenAI

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        # Timeout curto + sem retry automático: se o 9Router/modelo travar,
        # falha rápido em vez de deixar o job diário pendurado (mesmo
        # raciocínio do cliente em rag-knowledge-assistant).
        self._client = OpenAI(
            base_url=base_url, api_key=api_key or "not-needed", timeout=90.0, max_retries=1
        )

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""
