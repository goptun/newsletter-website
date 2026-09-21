"""Prompts para geração da edição diária — estrutura fixa (assunto curto,
Curiosidade do dia, um parágrafo por notícia com título curto em negrito +
desenvolvimento + atribuição de fonte), sem propaganda e sem comentário
editorial de cada notícia (ver
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
    "tecnologia. Gere UM parágrafo curto (1-2 frases) exatamente no formato "
    "'Curiosidade do dia: Em {data} de <ano>, <fato real e verificável de "
    "história da tecnologia/computação que aconteceu nesse dia e mês>.' — "
    "'<ano>' é o ano em que o fato ocorreu, nunca o ano atual. Não inclua "
    "nenhuma propaganda, call-to-action ou frase de transição do tipo 'E "
    "após as notícias de hoje'. Responda só com o parágrafo, em português "
    "do Brasil."
)

NEWS_SYSTEM = (
    "Você escreve um item de notícia para uma newsletter diária de "
    "tecnologia, com tom profissional e objetivo. Formato exato, em um único "
    "parágrafo: '<título>: <desenvolvimento> As informações são do site "
    "{source}.'\n"
    "- <título>: curto e direto, no máximo 8 palavras (até ~60 caracteres), "
    "sem dois-pontos, sem ponto final e sem repetir o desenvolvimento. Diz "
    "sobre o que é a notícia, não conta a notícia inteira.\n"
    "- <desenvolvimento>: 2 a 4 frases (cerca de 50 a 90 palavras) que "
    "explicam o que aconteceu, quem está envolvido, o contexto e os "
    "números/datas presentes no material. É aqui que a notícia é contada "
    "em detalhe — não repita o título com outras palavras.\n"
    "Sem opinião, sem comentário adicional, sem conclusão pessoal. "
    "Baseie-se exclusivamente no título e no texto fornecidos — não invente "
    "fatos, números ou declarações que não estejam neles. Mantenha nomes "
    "próprios de produtos e empresas como no original. Responda só com o "
    "parágrafo, em português do Brasil."
)

SUBJECT_SYSTEM = (
    "Você escreve a linha de assunto de uma newsletter diária de tecnologia. "
    "Deve ser curta e profissional: no máximo 60 caracteres, destacando o "
    "tema de 1 ou 2 das principais notícias do dia (não liste todas). Sem "
    "ponto final, sem emoji, sem aspas, sem linguagem alarmista ou de "
    "clickbait, e sem separadores como barra ou pipe. Responda só com a "
    "linha de assunto, em português do Brasil."
)


def curiosidade_prompt(today: date) -> tuple[str, str]:
    # Só dia e mês: o ano atual não entra no prompt pra não vazar pro texto
    # ("Em 21 de setembro de 1995, ..." — o ano é o do fato histórico).
    formatted = f"{today.day} de {_MESES_PT_BR[today.month]}"
    system = CURIOSIDADE_SYSTEM.format(data=formatted)
    user = f"Hoje é {formatted}."
    return system, user


def news_item_prompt(article: Article) -> tuple[str, str]:
    system = NEWS_SYSTEM.format(source=article.source)
    user = f"Título original: {article.title}\nTexto da fonte: {article.summary}\nURL: {article.url}"
    return system, user


def subject_prompt(top_titles: list[str]) -> tuple[str, str]:
    user = "Principais manchetes de hoje:\n" + "\n".join(f"- {t}" for t in top_titles)
    return SUBJECT_SYSTEM, user
