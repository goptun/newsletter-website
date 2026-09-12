"""Prompts para geração da edição diária — segue a estrutura de referência
observada em docs/newsletter_template.pdf e docs/newsletter_template_2.pdf,
mas sem o trecho de propaganda ("E após as notícias de hoje: ...") e sem o
comentário editorial de cada notícia (ver specs/newsletter/content-generation/spec.md)."""

from __future__ import annotations

from datetime import date

from app.news.feeds import Article

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
    formatted = today.strftime("%d de %B de %Y")
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
