"""Prompts para geração da edição diária — estrutura fixa (assunto curto,
Curiosidade do dia (fato real da Wikipedia, ver app/news/history.py), um parágrafo por notícia com título curto em negrito +
desenvolvimento + atribuição de fonte), sem propaganda e sem comentário
editorial de cada notícia (ver
specs/newsletter/content-generation/spec.md)."""

from __future__ import annotations

from datetime import date

from app.news.feeds import Article
from app.news.history import HistoricalEvent

# `date.strftime("%B")` depende do locale do sistema — o container de produção
# só tem C/C.utf8/POSIX instalados (sem pt_BR), então isso sempre devolveria o
# nome do mês em inglês ("September"). Mapeamento fixo evita a dependência.
_MESES_PT_BR = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}

CURIOSIDADE_PICK_SYSTEM = (
    "Você escolhe o fato histórico para a seção 'Curiosidade do dia' de uma "
    "newsletter diária de tecnologia, a partir de uma lista numerada de "
    "eventos reais ocorridos neste mesmo dia e mês. Ordem de preferência: "
    "(1) tecnologia, computação, internet ou telecomunicações; (2) "
    "exploração espacial, descobertas científicas ou invenções; (3) o fato "
    "mais curioso que sobrar. Em qualquer caso, evite guerras, armas, "
    "aeronaves ou veículos militares, mortes, crimes e política. Responda "
    "apenas com o número do item escolhido, por exemplo: 12"
)

CURIOSIDADE_WRITE_SYSTEM = (
    "Você escreve a seção 'Curiosidade do dia' de uma newsletter diária de "
    "tecnologia. A partir do fato histórico fornecido, escreva 1 ou 2 frases "
    "curtas em português do Brasil que descrevam o fato. Comece direto pelo "
    "fato: a data ('Em <dia> de <mês> de <ano>,') é adicionada depois, então "
    "NÃO escreva data, ano nem 'Curiosidade do dia' — a primeira letra deve "
    "ser minúscula, a menos que seja nome próprio. Baseie-se exclusivamente "
    "no texto fornecido: não acrescente detalhes, números, causas ou contexto "
    "que não estejam nele. Sem propaganda nem call-to-action. Responda só "
    "com o texto."
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
    "Sem opinião, sem comentário adicional, sem conclusão pessoal. Ignore "
    "trechos que não sejam a notícia em si: instruções de uso ou passo a "
    "passo (ex.: 'abra Configurações, toque em...'), menus, chamadas para "
    "assinar/comprar e avisos legais. "
    "Baseie-se exclusivamente no título e no texto fornecidos — não invente "
    "fatos, números ou declarações que não estejam neles. Se o texto for "
    "curto, escreva só 1 ou 2 frases: NUNCA complete com generalidades, "
    "recomendações, contexto de mercado, a data de publicação ou frases do "
    "tipo 'reforçando o compromisso...' que não estejam no texto. Mantenha "
    "nomes próprios de produtos e empresas como no original. Responda só "
    "com o parágrafo, em português do Brasil."
)

SUBJECT_SYSTEM = (
    "Você escreve a linha de assunto de uma newsletter diária de tecnologia. "
    "Deve ser curta e profissional: no máximo 60 caracteres, destacando o "
    "tema de 1 ou 2 das principais notícias do dia (não liste todas). Sem "
    "ponto final, sem emoji, sem aspas, sem linguagem alarmista ou de "
    "clickbait, e sem separadores como barra ou pipe. Responda só com a "
    "linha de assunto, em português do Brasil."
)


def format_day_month(today: date) -> str:
    return f"{today.day} de {_MESES_PT_BR[today.month]}"


def curiosidade_pick_prompt(events: list[HistoricalEvent]) -> tuple[str, str]:
    lines = [f"{i}. ({e.year}) {e.text[:200]}" for i, e in enumerate(events, start=1)]
    return CURIOSIDADE_PICK_SYSTEM, "Eventos deste dia:\n" + "\n".join(lines)


def curiosidade_write_prompt(event: HistoricalEvent) -> tuple[str, str]:
    return CURIOSIDADE_WRITE_SYSTEM, f"Ano: {event.year}\nFato: {event.text}"


def news_item_prompt(article: Article) -> tuple[str, str]:
    system = NEWS_SYSTEM.format(source=article.source)
    user = f"Título original: {article.title}\nTexto da fonte: {article.summary}\nURL: {article.url}"
    return system, user


def subject_prompt(top_titles: list[str]) -> tuple[str, str]:
    user = "Principais manchetes de hoje:\n" + "\n".join(f"- {t}" for t in top_titles)
    return SUBJECT_SYSTEM, user
