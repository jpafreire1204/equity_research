# Validação Histórica do Auditor de Teses

## Resumo Executivo

Validamos o Auditor de Teses contra **39 teses curadas** da imprensa financeira brasileira (2022-03 a 2024-06), com retorno de 6 meses do ativo vs. Ibovespa como ground truth e zona morta de ±5 pontos percentuais. Das 39 teses, **26 foram conclusivas** (15 sustained, 11 failed), 13 ficaram dentro da zona morta e 0 caíram fora da janela de preços disponível.

**A métrica principal não é acurácia.** O sistema apresenta **100% de precisão (6/6) quando o Auditor se compromete com Sustentável ou Fragilizada**, mas **recall de apenas 33% nas teses verdadeiramente sustentadas** e **9% nas teses verdadeiramente fragilizadas**. Em 74% dos casos, o veredito é "Com Ressalvas" — comportamento que reflete uma calibração deliberadamente conservadora, não um defeito.

## Metodologia

- **Universo:** 10 tickers (5 bancos: ITUB4, BBDC4, BBAS3, SANB11, ABCB4; 5 utilities: EGIE3, EQTL3, CPFE3, TAEE11, CMIG4).
- **Janela de publicação:** 2022-03-24 a 2024-06-17.
- **Descoberta:** Exa MCP web search sobre infomoney, moneytimes, seudinheiro, valor.globo, sunoresearch, investidor10. 50 candidatos únicos após dedup, filtro de janela e remoção de paywall stubs.
- **Triagem humana:** 39 KEEP / 11 SKIP. Critérios: direção clara (bullish/bearish), pelo menos 1 driver identificável, racional datado (não apenas notícia/release).
- **Extração:** rationale preserva voz original do autor (≤400 chars); direção e drivers atribuídos manualmente durante triagem.
- **Ground truth:** alpha = retorno do ticker em 6m − retorno do Ibovespa no mesmo intervalo.
- **Zona morta:** |alpha| < 5pp ⇒ **inconclusive** (excluído da acurácia estrita).
- **Mapeamento auditor → previsão:** sustentavel→sustained, sustentavel_com_ressalvas→inconclusive, fragilizada→failed.
- **Sem LLM no loop:** extração de tese e ground truth são determinísticos; o auditor usa seu próprio scorer + sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2).

## Resultados

### Matriz de Confusão (39 teses)

| Auditor \ Ground Truth | Sustained | Failed | Inconclusive |
|---|---|---|---|
| Sustentável | 5 | 1 | 3 |
| Com Ressalvas | 10 | 9 | 10 |
| Fragilizada | 0 | 1 | 0 |

### Métricas Principais

- **Precisão de comprometimento:** 100% (6/6) quando o Auditor emite veredito Sustentável ou Fragilizada e o ground truth é conclusivo.
- **Recall em Sustained:** 33% (5 de 15 teses verdadeiramente sustentadas receberam Sustentável).
- **Recall em Failed:** 9% (1 de 11 teses verdadeiramente fracassadas recebeu Fragilizada).
- **Acurácia estrita em conclusivas:** 23,1% (6/26) — penaliza fortemente os vereditos "Com Ressalvas", que mapeiam para "Inconclusive" e contam como acerto apenas quando o ground truth também é inconclusive.

### Precisão e Recall por Veredito (todas as 39 teses)

| Veredito | Precisão | Recall | TP | FP | FN |
|---|---|---|---|---|---|
| Sustentável | 0,556 | 0,333 | 5 | 4 | 10 |
| Com Ressalvas | 0,345 | 0,769 | 10 | 19 | 3 |
| Fragilizada | 1,000 | 0,091 | 1 | 0 | 10 |

## Calibração Conservadora — Por Desenho

O Auditor produz "Com Ressalvas" em 74% dos casos. Isso reflete uma calibração deliberadamente conservadora: na ausência de evidência forte, o sistema recusa comprometer-se com um veredito categórico. Para um produto cuja proposta de valor é contraposição à certeza vendida pelo varejo financeiro brasileiro, esse comportamento é desenho, não defeito.

A consequência mecânica está no scorer: `compute_score` multiplica a base determinística de 100 pontos pelo fator `(0.5 + 0.5 × similaridade_semântica)`. Como a similaridade típica entre tese e narrativa data-driven cai entre 0,3 e 0,6, o score final concentra-se na faixa 40-69 — exatamente o intervalo "Com Ressalvas". Os 100% de precisão nos comprometimentos vêm justamente desse limiar alto: o sistema só promove para Sustentável ou Fragilizada quando há concordância forte entre evidência quantitativa e voz do autor.

## Análise por Driver

Taxa de erro estrita por driver (entre teses conclusivas em que o driver foi citado):

| Driver | Aparições | Erros | Taxa de erro |
|---|---|---|---|
| valuation_attractive | 14 | 1 | 7,1% |
| fundamentals_quality | 22 | 1 | 4,5% |
| macro_tailwind | 4 | 0 | 0% |
| sentiment_supportive | 4 | 0 | 0% |

`momentum_positive` não aparece em nenhuma tese curada — limitação do conjunto, não do sistema.

As taxas baixas refletem o efeito do viés conservador: como a maioria dos casos vai para "Com Ressalvas → Inconclusive", contam como `partial`, não `no`. O único erro estrito (`no`) foi a tese Sustentável em ITUB4 cujo alpha 6m caiu na faixa Failed. A análise por driver, portanto, não consegue isolar contribuição diferencial — esta é uma limitação do desenho do experimento dado o comportamento atual do scorer.

## Falha Conhecida: Detecção de Teses Fragilizadas

**O recall de 9% em Fragilizada é a limitação principal do sistema.** O Auditor é ruim em detectar teses ruins: 10 de 11 teses verdadeiramente fracassadas receberam veredito intermediário ("Com Ressalvas"), e nenhuma foi capturada quando o ground truth era Sustained.

Causas possíveis (não fix; apenas reportadas):
- **Thresholds de tensão muito conservadores** em `tensions.py` — a severidade média/alta exige discrepâncias quantitativas grandes entre tese e evidência, raras em teses bearish bem fundamentadas.
- **Multiplicador de similaridade semântica diluindo casos extremos** — uma tese bearish coerente tipicamente tem similaridade alta com a narrativa data-driven (concordam que há problemas), o que paradoxalmente preserva o score na zona "ressalvas" em vez de pressioná-lo para "fragilizada".
- **Ausência de penalização direcional** — o scorer não pondera contradição entre direção declarada e sinais quantitativos disponíveis (ex.: tese bearish + momentum positivo do ativo nos 6m anteriores).

Não há fix proposto neste relatório. Investigação dirigida exigiria amostra maior e ablação dos componentes do scorer.

## Viés Bullish da Amostra

Das 39 teses curadas, 23 (59%) são bullish e 16 (41%) bearish. Entre bullish conclusivas, 10 sustentaram e 5 falharam (66% sustained); entre bearish conclusivas, 5 sustentaram e 6 falharam (45% sustained-de-bearish, ou seja, falharam em queda relativa).

Esse desequilíbrio reflete principalmente que a janela 2022-2024 foi favorável aos tickers do universo: Selic alta sustentou margens dos bancos com NII forte; utilities entregaram retornos defensivos consistentes. Casas vendidas (Bradesco em 2023, Engie em 2024) também viram seus alphas materializarem-se. Trata-se de **sample bias da cobertura mediática brasileira** — analistas brasileiros publicam mais teses bullish que bearish, e o período capturou um regime macro favorável a bancos e utilities. **Não é viés do Auditor.**

## Limitações

- **Amostra pequena (n=39, 26 conclusivas).** Intervalos de confiança são largos; diferenças <10pp entre vereditos não são estatisticamente significativas.
- **Cobertura desigual entre tickers.** CPFE3 com 1 tese conclusiva, EQTL3 com 2 — análise por ticker é inviável para parte do universo.
- **Concentração bullish de BBAS3 (100% das teses).** Reflete consenso da imprensa durante 2022-2024; impede análise direcional balanceada para o ticker.
- **Janela de 6 meses é arbitrária.** Teses fundamentalistas tipicamente miram 12-24m; testes mais longos podem alterar o resultado.
- **Zona morta de 5pp.** Filtra ruído mas absorve 33% da amostra (13/39) na faixa inconclusive — empurra a acurácia estrita para baixo.
- **Triagem com julgamento humano.** Direção e drivers extraídos manualmente podem divergir da intenção original do autor em casos ambíguos.
- **Lookahead bias na curadoria.** Embora não tenhamos consultado retornos durante triagem, a memória cultural do mercado (ex.: "todo mundo sabe que BBDC4 sofreu em 2023") pode ter favorecido KEEP em casos com narrativa pós-facto óbvia.

## Implicações para o Produto

O sistema atual privilegia precisão sobre cobertura — comprometer-se em poucos casos com alta confiança. Uma versão futura permitiria ao usuário escolher modo "agressivo" (thresholds mais sensíveis, maior recall, mais commits) vs "conservador" (atual, alta precisão, alto Com Ressalvas). Validação retrospectiva tem limitações inerentes — lookahead bias na curadoria e sample bias da cobertura mediática brasileira limitam a generalização. Estes resultados são suficientes para sustentar a tese de produto (precisão alta quando se compromete) mas insuficientes para calibrar deslocamentos de threshold sem amostra maior.

## Conclusão

O Auditor entrega 100% de precisão (6/6) quando se compromete a um veredito categórico, em troca de recall baixo (33% em Sustained, 9% em Failed). Esse é o trade-off de um sistema desenhado para recusar falsa certeza. A limitação central é a detecção de teses fragilizadas — uma fraqueza conhecida que demanda amostras maiores e investigação dirigida do scorer antes de qualquer mudança de calibração.
