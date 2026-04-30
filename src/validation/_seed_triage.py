"""Build triage.csv with first-pass direction/drivers/recommendation per candidate.

Classification logic uses the curated full_text from each candidate. The author voice
is preserved later in extraction; here we only label direction + drivers + KEEP/SKIP.
"""
from __future__ import annotations

import csv
from pathlib import Path

from src.validation.discovery import load_candidates, COMPANY_NAMES

DATA_DIR = Path("data/validation")
TRIAGE_PATH = DATA_DIR / "triage.csv"

# Triage decisions keyed by URL.
# direction: bullish | bearish | neutral | unclear
# drivers: subset of fundamentals_quality, valuation_attractive, momentum_positive, sentiment_supportive, macro_tailwind
# rec: KEEP | SKIP
# rationale: 1-line summary of author/article stance (PT-BR)
T = {
    # ===== ITUB4 =====
    "https://www.infomoney.com.br/mercados/por-que-o-itau-itub4-e-a-acao-preferida-da-xp-no-setor-bancario/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive", "macro_tailwind"],
        rec="KEEP",
        rationale="XP reitera compra; afrouxamento monetário reduz custo do funding, NPL abaixo do SFN, payout maior, valuation 6,8x P/L abaixo da média histórica."),
    "https://www.infomoney.com.br/mercados/itau-unibanco-itub4-tem-recomendacao-elevada-a-compra-com-avaliacao-atraente/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive"],
        rec="KEEP",
        rationale="BBI eleva para outperform por ROE superior, balanço forte, melhor risco/recompensa entre bancos brasileiros."),
    "https://www.infomoney.com.br/mercados/itau-itub4-acoes-resultado-banco-desponta-entre-pares-do-setor-mais-uma-vez-dizem-analistas/": dict(
        direction="bullish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="Resultado 2T23 reitera consistência: ROE 21,5%, qualidade de ativos sob controle, formação de inadimplência desacelerando."),
    "https://www.infomoney.com.br/onde-investir/itau-itub4-tem-espaco-para-dividendo-extraordinario-de-ate-r-14-bilhoes-avalia-xp/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive"],
        rec="KEEP",
        rationale="XP avalia espaço para dividendo extra de até R$14bi, payout subindo de 30% para 67,9%, DY dobraria de 4% para 9%."),
    "https://www.infomoney.com.br/mercados/as-acoes-do-itau-estao-caras-ou-baratas/": dict(
        direction="neutral",
        drivers=[],
        rec="SKIP",
        rationale="Artigo expositivo: P/VPA 1,79x não barata, P/L 9,07x médio, DY 8% atrativo — sem stance clara do autor."),
    "https://www.infomoney.com.br/mercados/itau-itub4-analistas-destacam-solidez-de-margens-financeiras-mas-apontam-queda-na-qualidade-de-ativos/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive"],
        rec="KEEP",
        rationale="Margens financeiras melhores que pares, ressalva em qualidade de ativos; BBI mantém outperform, valuation atrativo, preço-alvo R$32."),
    "https://www.infomoney.com.br/mercados/bofa-eleva-acao-do-itau-itub4-para-compra-e-elenca-7-temas-para-os-bancos-em-2024/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive", "sentiment_supportive"],
        rec="KEEP",
        rationale="BofA eleva ITUB4 para compra; valuation premium merecido por execução superior, top pick com BPAC11, preço-alvo R$40."),
    "https://www.infomoney.com.br/mercados/morgan-stanley-rebaixa-itau-itub4-e-elege-bradesco-bbdc4-como-favorito-entre-bancoes-de-olho-na-queda-da-selic/": dict(
        direction="bearish",
        drivers=["macro_tailwind"],
        rec="KEEP",
        rationale="MS rebaixa Itaú para equalweight: ciclo de queda da Selic prejudicou Itaú mais que pares historicamente, sensibilidade negativa."),
    "https://www.infomoney.com.br/mercados/itau-itub4-morgan-eleva-adr-a-compra-com-selic-alta-valuation-e-bons-dividendos/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive", "sentiment_supportive"],
        rec="KEEP",
        rationale="MS eleva ADR para overweight; Selic alta por mais tempo, valuation atrativo, papel defensivo, DY 7%, execução de alto nível."),

    # ===== BBDC4 =====
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-reietera-recomendacao-venda/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="BBA reitera underperform; safras ruins de crédito mais longas, capital baixo vs pares, recuperação lenta — não acompanhar rali."),
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-por-que-o-morgan-stanley-segue-otimista-indo-contra-a-cautela-geral-do-mercado/": dict(
        direction="bullish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="MS overweight contra cautela geral; recuperação do ROE pode ocorrer mais cedo que tarde, foco em digitalização e racionalização."),
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-desempenho-acoes-resultado-fraco-e-comprova-que-recuperacao-da-rentabilidade-sera-lenta-apontam-analistas/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="2T23 fraco confirma recuperação lenta; XP vê inflexão mais distante, guidance revisado para baixo, NIM enfraquecida."),
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-tem-resultado-fraco-mas-superando-projecoes-desempenho-acoes-como-os-numeros-do-1o-tri-reacendem-o-debate-sobre-os-ativos/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="1T23 fraco supera projeções mas reacende debate; lucro 37% menor que 1T22, ROE bem abaixo de rivais — casa mantém underperform."),
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-acao-queda-alem-de-americanas-numeros-fracos-4o-tri-projecoes-uns-2023-analistas-reforcam-pessimismo/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="4T22 fraco e guidance 2023 negativo; BBA reitera underperform, NII fraco e provisões altas devem manter ROEs abaixo do custo de capital."),
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-acao-queda-alem-de-americanas-numeros-fracos-4o-tri-projecoes-ruins-2023-analistas-reforcam-pessimismo/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="4T22 fraco e guidance 2023 negativo; BBA reitera underperform, NII fraco e provisões altas devem manter ROEs abaixo do custo de capital."),
    "https://www.infomoney.com.br/mercados/itau-bba-corta-acao-bradesco-bbdc4-para-venda-ve-tempestade-perfeita-para-lucros-entre-2023-e-2024-e-alerta-para-efeito-americanas/": dict(
        direction="bearish",
        drivers=["fundamentals_quality", "macro_tailwind"],
        rec="KEEP",
        rationale="BBA corta para underperform: tempestade perfeita 2023-2024 (carteira menor, NIMs caem, custos de crédito sobem); ROE abaixo do custo de capital."),
    "https://www.infomoney.com.br/mercados/apos-jp-bradesco-bbdc4-tem-recomendacao-cortada-pelo-itau-bba-com-deterioracao-da-qualidade-do-credito/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="BBA corta para market perform; deterioração da qualidade do crédito e NII fraca, projeções de lucros reduzidas."),
    "https://www.infomoney.com.br/mercados/credit-suisse-rebaixa-banco-do-brasil-bbas3-eleva-bradesco-bbdc4-e-mantem-itau-itub4-como-top-pick-entre-bancoes-de-olho-selic/": dict(
        direction="neutral",
        drivers=["valuation_attractive"],
        rec="SKIP",
        rationale="Credit eleva BBDC4 só de underperform para neutra — valuation mais justo mas casa ainda prefere Itaú; sem tese bull/bear forte."),

    # ===== BBAS3 =====
    "https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-apos-recorde-em-2023-ate-onde-acao-da-estatal-pode-ir-neste-ano/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive"],
        rec="KEEP",
        rationale="Genial recomenda compra com PA R$64,90; ROE 20,7%, lucro recorde, BB supera bancos privados — apesar da cautela após rali."),
    "https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-balanco-nao-foi-tao-bom-quanto-parece-mas-guidance-e-dividendos-guiam-animo-desempenho-acoes/": dict(
        direction="bullish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="Guidance 2024 forte (R$37-40bi) com payout subindo de 40% para 45%; ROE próximo de 21%, Citi compra com PA R$74."),
    "https://www.infomoney.com.br/onde-investir/como-serao-os-dividendos-de-bbas3-sob-a-gestao-de-tarciana-medeiros-mercado-projeta-taxas-de-ate-137/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive"],
        rec="KEEP",
        rationale="4 de 7 analistas recomendam compra, DY projetado 6,4-13,7%; banco negocia próximo das mínimas em P/VP mesmo com resultados históricos."),
    "https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-acoes-estao-caras-ou-baratas/": dict(
        direction="bullish",
        drivers=["valuation_attractive"],
        rec="KEEP",
        rationale="BB negocia P/L 4,47x e P/VPA 0,88x — papel descontado; risco político não materializou, DY 10-12% torna tese atrativa."),
    "https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-e-mais-uma-vez-o-campeao-de-lucro-e-roe-entre-os-bancoes-o-que-esperar-para-a-acao/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive"],
        rec="KEEP",
        rationale="BBA: NII +8% no tri, melhor entre grandes, P/B 0,7x e P/L 3,4x para 2024 — compra com PA R$56; Genial PA R$62,80."),
    "https://www.infomoney.com.br/mercados/bb-bbas3-seguira-com-rentabilidade-alta-como-os-analistas-veem-a-estrategia-do-banco/": dict(
        direction="bullish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="ROE acima de 20% sustentável; mix da carteira alinha retorno e qualidade; XP eleva PA de R$61 para R$73."),
    "https://www.infomoney.com.br/mercados/por-que-as-acoes-do-banco-do-brasil-bbas3-estao-entre-as-preferidas-do-itau-bba-para-2024/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive", "sentiment_supportive"],
        rec="KEEP",
        rationale="BBA reitera outperform, top pick: BB oferece valor, crescimento e DY 12%; ROE ~21%, P/VPA 0,8x e P/L 4x ainda descontados."),
    "https://www.infomoney.com.br/onde-investir/dividendos-bancos-baratos-bbas3-sanb11-bbdc4-itub4/": dict(
        direction="bullish",
        drivers=["valuation_attractive"],
        rec="KEEP",
        rationale="BB apontado como melhor para dividendos 2023, P/L 3,44x abaixo da média 5y, DY projetado 11%; preço-teto até R$52."),

    # ===== SANB11 =====
    "https://www.infomoney.com.br/mercados/santander-bbi-eleva-sanb11-de-venda-a-compra-tempos-ruins-nao-duram-para-sempre/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive"],
        rec="KEEP",
        rationale="BBI eleva de venda para compra; perspectiva de maior rentabilidade após limpeza do balanço, ROE 16-17,5% em 2024-2025, desconto 20-22% vs histórico."),
    "https://www.infomoney.com.br/mercados/santander-brasil-sanb11-mostra-melhora-mas-ainda-tem-longo-caminho-a-percorrer-como-os-analistas-viram-o-balanco-do-2o-tri/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="Apesar de melhora no balanço 2T23, Citi/BBI/XP mantêm underperform/neutra; NIM cai 20bp, formação de NPL ainda mostra longo caminho."),
    "https://www.infomoney.com.br/mercados/santander-brasil-sanb11-mostra-a-tao-esperada-recuperacao-da-qualidade-dos-ativos-no-3o-tri-com-queda-da-inadimplencia-desempenho-acoes/": dict(
        direction="neutral",
        drivers=["fundamentals_quality"],
        rec="SKIP",
        rationale="Resultado 3T23 mostra recuperação mas ROE 13,1% ainda fraco; analistas seguem cautelosos (BBI underperform, Goldman venda, XP neutra) — sem stance unificada."),
    "https://www.infomoney.com.br/mercados/acoes-xp-ve-2023-desafiador-para-bancos-destaca-itau-itub4-como-preferido-e-eleva-santander-sanb11-a-neutro/": dict(
        direction="neutral",
        drivers=["valuation_attractive"],
        rec="SKIP",
        rationale="XP eleva apenas para neutra — assimetria negativa anterior ajustada, ação com preço justo, sem direção clara."),

    # ===== ABCB4 =====
    "https://www.infomoney.com.br/mercados/abc-brasil-abcb4-ve-lucro-subir-a-r-232-mi-mas-analistas-veem-tendencias-mistas-e-acao-cai/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="BBI/BBA neutras com viés negativo: NII em desaceleração no segmento médio, deterioração da inadimplência, NIMs comprimidos, fraco impulso operacional."),
    "https://www.infomoney.com.br/mercados/abc-brasil-abcb4-mesmo-com-patrimonio-remunerado-pelo-cdi-banco-ve-juros-mais-baixos-como-vetor-de-crescimento/": dict(
        direction="bullish",
        drivers=["macro_tailwind", "valuation_attractive"],
        rec="KEEP",
        rationale="Queda dos juros destrava plano de crescimento; BTG compra PA R$25, valuation descontado, sólidas vias de crescimento."),
    "https://www.infomoney.com.br/onde-investir/small-caps-ou-blue-chips-dividendos-queda-selic/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "macro_tailwind", "sentiment_supportive"],
        rec="KEEP",
        rationale="ABCB4 preferida das small caps em setores perenes; banco lucrativo, negocia abaixo do VP, DY 8%, deve se beneficiar da queda da Selic."),
    "https://www.infomoney.com.br/onde-investir/banco-abc-brasil-abcb4-reforma-dividendos-fim-jcp/": dict(
        direction="neutral",
        drivers=[],
        rec="SKIP",
        rationale="Reportagem sobre estratégia de payout e fim do JCP, sem direção clara da tese (artigo de gestão da empresa)."),

    # ===== EGIE3 =====
    "https://www.infomoney.com.br/mercados/engie-egie3-jpmorgan-nao-ve-potencial-de-valorizacao-e-corta-recomendacao-do-papel-para-venda/": dict(
        direction="bearish",
        drivers=["valuation_attractive", "fundamentals_quality"],
        rec="KEEP",
        rationale="JPM corta para venda; TIR 8,6% apertada, alavancagem 3,5x após Atlas+capex, mercado pessimista com renováveis em preços baixos."),
    "https://www.infomoney.com.br/mercados/engie-egie3-esta-menos-atrativa-itau-bba-revisa-geradoras-e-corta-recomendacao/": dict(
        direction="bearish",
        drivers=["valuation_attractive"],
        rec="KEEP",
        rationale="BBA corta de compra para neutra; TIR 8% pouco atrativa vs NTN-B, capex aumentará alavancagem, payout cai de 100% para 55% — perde apelo de dividendos."),
    "https://www.infomoney.com.br/onde-investir/acoes-recomendadas-dividendos-maio-2023/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "sentiment_supportive"],
        rec="KEEP",
        rationale="Engie nova quase unanimidade entre dividendos; 6 portfólios recomendam, sólida geração de caixa, payout mínimo 55%, contratos novos para 2022-27."),
    "https://www.infomoney.com.br/mercados/engie-brasil-egie3-reduziu-dividendos-para-nao-deixar-de-aproveitar-oportunidades-diz-cfo-acoes-caem-apos-balanco/": dict(
        direction="neutral",
        drivers=[],
        rec="SKIP",
        rationale="Reportagem de balanço 2T23: dividendos reduzidos, CFO comenta cautela; XP neutra, BBI outperform — analistas divididos, sem direção predominante."),

    # ===== EQTL3 =====
    "https://www.infomoney.com.br/mercados/enel-mais-perto-de-vender-a-coelce-coce3-quais-os-impactos-para-as-possiveis-compradoras-equatorial-eqtl3-e-cpfl-cpfe3/": dict(
        direction="neutral",
        drivers=[],
        rec="SKIP",
        rationale="Reportagem de M&A; BBI mantém neutra para EQTL3, sem tese forte (depende de comprar a Coelce ou não)."),
    "https://www.infomoney.com.br/mercados/equatorial-eqtl3-nao-ve-retorno-atraente-nos-proximos-leiloes-de-transmissao/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "sentiment_supportive"],
        rec="KEEP",
        rationale="Resultados 4T21 sólidos; Credit Suisse vê EQTL3 como uma das favoritas, história de diversificação, crescimento e qualidade."),
    "https://www.infomoney.com.br/mercados/equatorial-eqtl3-salta-apos-ser-unica-a-entregar-oferta-por-sabesp-sbsp3-tem-queda/": dict(
        direction="bullish",
        drivers=["sentiment_supportive", "fundamentals_quality"],
        rec="KEEP",
        rationale="Genial vê positivo: Equatorial com excelente track-record na gestão de concessões, mercado reagiu com +6,29% após oferta única na Sabesp."),
    "https://www.infomoney.com.br/mercados/equatorial-eqtl3-adquire-celg-d-distribuidora-de-energia-de-goias-por-um-valor-total-r-75-bilhoes/": dict(
        direction="neutral",
        drivers=[],
        rec="SKIP",
        rationale="Reportagem de aquisição da Celg-D; sem opinião fundamentalista de analistas, apenas anúncio do deal."),

    # ===== CPFE3 =====
    "https://www.infomoney.com.br/onde-investir/8-acoes-de-dividendos-indicadas-para-julho-cpfe3-estreia-entre-os-destaques/": dict(
        direction="bullish",
        drivers=["valuation_attractive", "sentiment_supportive"],
        rec="KEEP",
        rationale="BTG: CPFE3 negociada a TIR real 10,2%, fortes resultados operacionais, payout 100% nos últimos 2 anos — fundamental para excelente desempenho 2022."),
    "https://www.infomoney.com.br/mercados/cpfl-cpfe3-tem-lucro-liquido-de-r-137-bilhao-no-quarto-trimestre-alta-de-33-no-ano/": dict(
        direction="neutral",
        drivers=[],
        rec="SKIP",
        rationale="Reportagem de balanço 4T22, sem opinião de analistas ou tese clara."),

    # ===== TAEE11 =====
    "https://www.infomoney.com.br/onde-investir/taesa-taee11-dividendos-moderados-2023-conheca-nova-eletrica-favorita-dos-analistas/": dict(
        direction="neutral",
        drivers=["fundamentals_quality"],
        rec="SKIP",
        rationale="Casas divididas: 10 manter, 3 compra, 3 venda; XP/VG manter por falta de upside, Suno venda — sem stance dominante do autor."),
    "https://www.infomoney.com.br/mercados/taesa-taee11-busca-equilibrio-dividendos-crescimento-alavancagem-acoes-caem-balanco/": dict(
        direction="bearish",
        drivers=["valuation_attractive", "fundamentals_quality"],
        rec="KEEP",
        rationale="MS underweight (PA R$35), BBA underperform (PA R$35,95) após 4T22; ação pouco atraente, alavancagem subindo (>4x) por capex de novos projetos."),
    "https://www.infomoney.com.br/mercados/alupar-alup11-isa-cteep-trpl4-e-taesa-taee11-pagam-bons-dividendos-mas-por-que-a-xp-nao-recomenda-compra-para-as-acoes/": dict(
        direction="bearish",
        drivers=["valuation_attractive"],
        rec="KEEP",
        rationale="XP neutra PA R$26: TIR real alavancada de 6,2% vs 7,1% dos pares e em linha com NTN-B — chamada de Taesa já se concretizou, sem upside."),
    "https://www.infomoney.com.br/onde-investir/dividendos-de-energia-taee11-trpl4-ou-alup11-veja-quanto-r-5-mil-rendem-nelas/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="Melver: Taesa em estágio mais maduro, gestão pouco ativa em leilões, alavancagem 3,7x maior das três — ISA CTEEP mais promissora; volume de pagamentos pode diminuir."),

    # ===== CMIG4 =====
    "https://www.infomoney.com.br/mercados/cemig-cmig4-da-privatizacao-a-federalizacao-tese-para-acoes-tem-forte-virada-e-traz-duvidas-no-mercado-o-que-esperar/": dict(
        direction="bearish",
        drivers=["fundamentals_quality", "valuation_attractive"],
        rec="KEEP",
        rationale="Federalização negativa para a tese; BBI estima TIR real subiria para 15-17% se federalizada, implicando queda adicional de 21-33% (PA R$8,90-7,50)."),
    "https://www.infomoney.com.br/mercados/jpmorgan-eleva-cemig-cmig4-e-camil-caml3-compra-rebaixa-alupar-alup11-e-mantem-marcopolo-pomo4-top-pick-acoes-reagem/": dict(
        direction="bullish",
        drivers=["fundamentals_quality", "valuation_attractive"],
        rec="KEEP",
        rationale="JPM eleva para compra; Cemig com TIR implícita 12,2% (>setor 11,6%), 5x EV/Ebitda, PA R$16, upside 29%, retorno total 42%."),
    "https://www.infomoney.com.br/mercados/cemig-cmig4-cai-mais-de-10-com-noticia-de-que-governo-de-mg-aceitou-repassar-ativos-para-abater-divida-com-uniao/": dict(
        direction="bearish",
        drivers=["fundamentals_quality"],
        rec="KEEP",
        rationale="Notícia de federalização derruba ação 9,71%; bancos não compram com fraqueza, BBA: difícil encontrar conforto em ponto de entrada."),
    "https://www.infomoney.com.br/mercados/cemig-cmig4-se-prepara-internamente-para-privatizacao-e-divulga-plano-para-investir-r-422-bi-ate-2027/": dict(
        direction="neutral",
        drivers=[],
        rec="SKIP",
        rationale="Reportagem sobre plano estratégico de investimentos da Cemig; conteúdo majoritariamente corporativo, sem análise de tese."),
}


def main() -> None:
    rows = []
    tickers = list(COMPANY_NAMES.keys())
    for tkr in tickers:
        for c in load_candidates(tkr):
            url = c["url"]
            t = T.get(url)
            if t is None:
                t = dict(direction="unclear", drivers=[], rec="SKIP",
                         rationale="(missing triage entry)")
            rows.append({
                "url": url,
                "ticker": c["ticker"],
                "published_date": c["published_date"],
                "author": c["author"],
                "direction": t["direction"],
                "drivers_mentioned": "|".join(t["drivers"]),
                "thesis_summary": t["rationale"],
                "triage_recommendation": t["rec"],
            })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with TRIAGE_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "url", "ticker", "published_date", "author",
            "direction", "drivers_mentioned", "thesis_summary",
            "triage_recommendation",
        ])
        w.writeheader()
        w.writerows(rows)

    keep = [r for r in rows if r["triage_recommendation"] == "KEEP"]
    skip = [r for r in rows if r["triage_recommendation"] == "SKIP"]
    print(f"Total candidates: {len(rows)}")
    print(f"  KEEP: {len(keep)}")
    print(f"  SKIP: {len(skip)}")
    print()
    by_ticker_dir = {}
    for r in keep:
        key = (r["ticker"], r["direction"])
        by_ticker_dir[key] = by_ticker_dir.get(key, 0) + 1
    print("KEEP by ticker × direction:")
    for tkr in tickers:
        bull = by_ticker_dir.get((tkr, "bullish"), 0)
        bear = by_ticker_dir.get((tkr, "bearish"), 0)
        print(f"  {tkr:7s} bullish={bull} bearish={bear}")


if __name__ == "__main__":
    main()
