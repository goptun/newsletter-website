"""Prompts para geração da edição diária — estrutura fixa (assunto, Curiosidade
do dia, um parágrafo por notícia com atribuição de fonte), sem propaganda e
sem comentário editorial de cada notícia (ver
specs/newsletter/content-generation/spec.md)."""

from __future__ import annotations

from datetime import date

from app.news.feeds import Article

# `date.strftime("%B")` depende do locale do sistema — o container de produção
# só tem C/C.utf8/POSIX instalados (sem pt_BR), então isso sempre devolveria o
# nome do mês em inglês ("September"). Mapeamento fixo evita a dependência.
_MESES_PT_BR = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}

CURIOSIDADE_SYSTEM = (
    "Você escreve a seção 'Curiosidade do dia' de uma newsletter diária de "
    "tecnologia. Gere UM parágrafo curto (1-2 frases) no formato "
    "'Curiosidade para o dia {data}: <fato real e verificável de história da "
    "tecnologia/computação relacionado a essa data>.' Não inclua nenhuma "
    "propaganda, call-to-action ou frase de transição do tipo 'E após as "
    "notícias de hoje'. Responda só com o parágrafo, em português do Brasil."
)

NEWS_SYSTEM = (
    "Você escreve um item de notícia objetivo para uma newsletter diária de "
    "tecnologia, no estilo: uma frase-manchete seguida de dois-pontos, o "
    "resumo factual da notícia (sem opinião, sem comentário adicional, sem "
    "conclusão pessoal), terminando com a frase 'As informações são do site "
    "{source}.'. Baseie-se exclusivamente no título e resumo fornecidos — "
    "não invente fatos, números ou declarações que não estejam neles. "
    "Responda só com o parágrafo, em português do Brasil."
)

SUBJECT_SYSTEM = (
    "Você escreve a linha de assunto de uma newsletter diária de tecnologia, "
    "resumindo 2 a 3 das principais notícias em fragmentos curtos separados "
    "por ' / ', no estilo 'Tema 1 / Tema 2 / Tema 3'. Responda só com a "
    "linha de assunto, sem aspas."
)


def curiosidade_prompt(today: date) -> tuple[str, str]:
    formatted = f"{today.day:02d} de {_MESES_PT_BR[today.month]} de {today.year}"
    system = CURIOSIDADE_SYSTEM.format(data=formatted)
    user = f"Data de hoje: {formatted}."
    return system, user


def news_item_prompt(article: Article) -> tuple[str, str]:
    system = NEWS_SYSTEM.format(source=article.source)
    user = f"Título: {article.title}\nResumo/fonte: {article.summary}\nURL: {article.url}"
    return system, user


def subject_prompt(top_titles: list[str]) -> tuple[str, str]:
    user = "Principais manchetes de hoje:\n" + "\n".join(f"- {t}" for t in top_titles)
    return SUBJECT_SYSTEM, user
