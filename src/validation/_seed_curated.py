"""Build curated_theses.json from triage.csv KEEP rows.

Rationale field uses author voice from the candidate full_text — clipped to ≤400 chars.
We do NOT paraphrase into auditor-friendly language; that would bias validation.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from src.validation.discovery import COMPANY_NAMES, load_candidates
from src.validation.extraction import clip_rationale, save_curated

DATA_DIR = Path("data/validation")
TRIAGE_PATH = DATA_DIR / "triage.csv"

# Per-URL author-voice rationale (extracted from full_text, ≤400 chars, original phrasing).
RATIONALES = {
    # ITUB4
    "https://www.infomoney.com.br/mercados/por-que-o-itau-itub4-e-a-acao-preferida-da-xp-no-setor-bancario/":
        "XP mantém compra: banco se beneficiará do ciclo de afrouxamento monetário, NPL abaixo da média do SFN sustenta dinâmica positiva dos lucros, capital saudável abre espaço para payout mais alto. Itaú negocia 6,8x P/L e 1,3x P/VPA, abaixo dos múltiplos históricos de 7,9x e 1,6x — desconto exagerado.",
    "https://www.infomoney.com.br/mercados/itau-unibanco-itub4-tem-recomendacao-elevada-a-compra-com-avaliacao-atraente/":
        "BBI eleva para outperform: Itaú oferece relação risco-recompensa atraente, principais riscos já precificados. Pode continuar apresentando forte crescimento de lucros e ROE superior. Balanço forte, com elevado índice de cobertura. Avaliação atrativa com margem de segurança significativa, melhor risco/recompensa entre bancos brasileiros.",
    "https://www.infomoney.com.br/mercados/itau-itub4-acoes-resultado-banco-desponta-entre-pares-do-setor-mais-uma-vez-dizem-analistas/":
        "Resultado 2T23 reitera estratégia de focar em clientes de baixo risco mantendo crescimento de margens. Credit Suisse: Itaú mostrou consistência e capacidade de gerir custos, ROE de 21,5% no Brasil, qualidade de ativos sob controle, formação de inadimplência desacelerando. MS: outro trimestre consistente e sólido.",
    "https://www.infomoney.com.br/onde-investir/itau-itub4-tem-espaco-para-dividendo-extraordinario-de-ate-r-14-bilhoes-avalia-xp/":
        "XP: há espaço para dividendo extra de até R$14bi. Itaú terá alívio em capital com Basileia faseada de 2025-2028. Forte reputação como bom administrador de capital, histórico de payout médio de 74,7% entre 2017-2019. Se concretizado, payout sobe de 30% para 67,9%, DY mais que dobra de 4% para 9%.",
    "https://www.infomoney.com.br/mercados/itau-itub4-analistas-destacam-solidez-de-margens-financeiras-mas-apontam-queda-na-qualidade-de-ativos/":
        "Resultados do 2T22 acima do esperado, melhores margens financeiras que pares com ressalva quanto à qualidade dos ativos em cartões e empréstimos pessoais. JP: Itaú se saiu melhor que pares na qualidade de ativos. BBI mantém outperform com PA R$32, justificando que o papel é negociado com valuation atrativo.",
    "https://www.infomoney.com.br/mercados/bofa-eleva-acao-do-itau-itub4-para-compra-e-elenca-7-temas-para-os-bancos-em-2024/":
        "BofA eleva ITUB4 para compra: valuation premium é merecido dada execução superior, top pick ao lado de BPAC11. PA elevado de R$33 para R$40 (upside 20%). Para 2024: inadimplência atingindo o pico, crescimento da carteira em ponto de inflexão, normalização da margem, espaço para reclassificação dos múltiplos.",
    "https://www.infomoney.com.br/mercados/morgan-stanley-rebaixa-itau-itub4-e-elege-bradesco-bbdc4-como-favorito-entre-bancoes-de-olho-na-queda-da-selic/":
        "MS rebaixa Itaú de overweight para equalweight, reduz PA de US$7,20 para US$6,80. 'Estamos rebaixando dada a extensa evidência de baixo desempenho quando as taxas caem. Difícil ignorar resultados menos favoráveis do banco como reação à queda das taxas no passado'. Sensibilidade mais alta a queda de juros que pares.",
    "https://www.infomoney.com.br/mercados/itau-itub4-morgan-eleva-adr-a-compra-com-selic-alta-valuation-e-bons-dividendos/":
        "MS eleva ADR para overweight, PA US$7,50 para US$8 (upside 38%). Selic alta por mais tempo, valuation atrativo, papel defensivo em piora macro/política, forte execução. ADRs corrigiram 17% no ano — ponto de entrada atrativo. Itaú lidera bancos tradicionais na transformação digital. DY 7%.",

    # BBDC4
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-reietera-recomendacao-venda/":
        "BBA reitera underperform com PA R$15: 'Bradesco provavelmente terá que lidar com safras ruins de crédito por mais tempo do que concorrentes, que já estão mais avançados em domar NPLs. Banco também tem menos espaço, em provisões e capital, para acelerar muito cedo'. Carteira deve crescer apenas 5% em 2023.",
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-por-que-o-morgan-stanley-segue-otimista-indo-contra-a-cautela-geral-do-mercado/":
        "MS mantém overweight contra cautela geral. Após reunião com Marcelo Noronha, MS saiu mais confiante de que recuperação do ROE 'poderá ocorrer mais cedo do que mais tarde'. Foco em digitalização e racionalização da abrangência do banco como principais catalisadores para redução de custos. Migração para nuvem termina em 2025.",
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-desempenho-acoes-resultado-fraco-e-comprova-que-recuperacao-da-rentabilidade-sera-lenta-apontam-analistas/":
        "Resultados do 2T23 mostram banco com dificuldades para crescer e rentabilizar carteira; conclusão praticamente unânime. XP: 'Acreditamos numa curva de melhoria, mas vemos o ponto de inflexão um pouco mais distante'. Bradesco revisou guidance para baixo (carteira de 6,5-9,5% para 1-5%). Margem financeira fraca.",
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-tem-resultado-fraco-mas-superando-projecoes-desempenho-acoes-como-os-numeros-do-1o-tri-reacendem-o-debate-sobre-os-ativos/":
        "Resultados do 1T23 trazem risco negativo para estimativas de 2023. Lucro de R$4,3bi foi 37% menor que 1T22 e ROE bem abaixo de rivais. Provisões altas, carteira contraiu 2,2% no trimestre, margem financeira enfraqueceu 2,4%. Casa mantém underperform.",
    "https://www.infomoney.com.br/mercados/bradesco-bbdc4-acao-queda-alem-de-americanas-numeros-fracos-4o-tri-projecoes-ruins-2023-analistas-reforcam-pessimismo/":
        "BBA: 'Estimamos R$20bi de lucro líquido (ROE 12%), abaixo das estimativas do mercado em R$25bi. NII fraco e altas despesas de provisão provavelmente manterão os ROEs abaixo do custo de capital em 2023 e 2024'. BBA reitera underperform; demorará até que o Bradesco recupere dos atuais 0,9x P/VPA.",
    "https://www.infomoney.com.br/mercados/itau-bba-corta-acao-bradesco-bbdc4-para-venda-ve-tempestade-perfeita-para-lucros-entre-2023-e-2024-e-alerta-para-efeito-americanas/":
        "BBA corta de marketperform para underperform: 'Vemos uma tempestade perfeita para os lucros de 2023-2024. A carteira de empréstimos crescerá menos, enquanto os NIMs dos clientes enfraquecerão e os custos de crédito irão subir'. Lucro estimado em R$20,4bi para 2023 e R$24bi para 2024 (ROE 13% e 14%).",
    "https://www.infomoney.com.br/mercados/apos-jp-bradesco-bbdc4-tem-recomendacao-cortada-pelo-itau-bba-com-deterioracao-da-qualidade-do-credito/":
        "BBA corta de outperform para market perform, reduz PA de R$23 para R$21 (upside apenas 2,6%). 'Reclassificação em função da deterioração da qualidade do crédito e da margem financeira líquida'. Projeta resultados fracos no 3T22, índices de inadimplência de varejo em alta, contaminação da carteira PME.",

    # BBAS3
    "https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-apos-recorde-em-2023-ate-onde-acao-da-estatal-pode-ir-neste-ano/":
        "Genial recomenda compra com PA R$64,90: 'Antecipamos outro trimestre positivo para o Banco do Brasil e projetamos um 2024 sem grandes surpresas, mantendo consistência'. Lucro 2023 projetado em R$35bi, ROE 20,7%. 'Esse desempenho supera significativamente vários bancos privados'.",
    "https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-balanco-nao-foi-tao-bom-quanto-parece-mas-guidance-e-dividendos-guiam-animo-desempenho-acoes/":
        "Genial: 'Guidance aponta para mais um ano de lucro robusto. ROE deve se manter em patamares bem elevados próximo de 21%, competindo com o Itaú em rentabilidade'. BB elevou payout de 40% para 45% (DY projetado 10%). Citi: 'Payout mais alto era requisição recorrente — deve levar a reclassificação dos ativos'. Compra PA R$74.",
    "https://www.infomoney.com.br/onde-investir/como-serao-os-dividendos-de-bbas3-sob-a-gestao-de-tarciana-medeiros-mercado-projeta-taxas-de-ate-137/":
        "Quatro de sete analistas recomendam compra de BBAS3 para 2023, DY estimado de 6,4% a 13,7%. Tahara (Benndorf): 'Banco negocia próximo das mínimas, em P/VP, mesmo com resultados históricos. Risco de governança é menor se comparado aos anos de 2014 e 2015'. Reis (Suno) projeta DY 10-12%, 'maiores dividendos da história do banco'.",
    "https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-acoes-estao-caras-ou-baratas/":
        "BB negocia com P/L 4,47x abaixo dos pares e P/VPA 0,88x — 'barato' pelas métricas. Rabelo (VG): papéis seguem descontados, risco político antecipado desde 2022 não se materializou. Nascimento (Levante): atratividade da tese é o avanço em consignado e agro, com assimetria. DY próximo de 10-12% torna o papel ainda mais atrativo.",
    "https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-e-mais-uma-vez-o-campeao-de-lucro-e-roe-entre-os-bancoes-o-que-esperar-para-a-acao/":
        "BBA: NII +8% no trimestre, maior crescimento entre grandes bancos. 'Esperamos que ações permaneçam positivas, negociando a 0,7x P/B e 3,4x P/L em 2024'. BBA tem compra com PA R$56. Genial reitera comprar com PA R$62,80, vendo múltiplos do banco estatal como atrativos. Ainda muito descontado depois de subir 41% YTD.",
    "https://www.infomoney.com.br/mercados/bb-bbas3-seguira-com-rentabilidade-alta-como-os-analistas-veem-a-estrategia-do-banco/":
        "Estratégia de crédito do BB ajudará a manter rentabilidade acima de 20%. Genial: 'BB deve continuar entregando boa rentabilidade (ROE 21%) em 2024, com condições de replicar nos anos subsequentes'. XP eleva PA de R$61 para R$73 (upside 26%), mantém compra. ROE em crescente: era <10% em 2016.",
    "https://www.infomoney.com.br/mercados/por-que-as-acoes-do-banco-do-brasil-bbas3-estao-entre-as-preferidas-do-itau-bba-para-2024/":
        "BBA reitera outperform e eleva PA de R$59 para R$65: 'BB oferece valor, crescimento e forte rendimento de dividendo de 12%'. ROE acima do setor de 21%. Apesar do rali de 76% em 2023, ações permanecem com desconto, negociadas a 0,8x P/VPA e 4x P/L. 'Em cada trimestre sucessivo BB obtém revisões para cima e re-rates'.",
    "https://www.infomoney.com.br/onde-investir/dividendos-bancos-baratos-bbas3-sanb11-bbdc4-itub4/":
        "BB apontado como melhor alternativa do setor para dividendos em 2023, DY projetado de 11%. P/L para 2023 de 3,44x (vs média 5y de 6,9x), DY 12,17% nos últimos 12 meses, situação 'barata'. Recomendam compra: Benndorf, Ticker, GuiaInvest, VG Research, L4 Capital — preço-teto R$41,50 a R$52.",

    # SANB11
    "https://www.infomoney.com.br/mercados/santander-bbi-eleva-sanb11-de-venda-a-compra-tempos-ruins-nao-duram-para-sempre/":
        "BBI eleva SANB11 de venda para compra: 'Tempos ruins não duram para sempre, chegou a hora de Comprar!'. Combinação benigna de crescimento mais rápido, portfólio mais adequado, maiores ganhos comerciais e menor custo do risco. ROE 16% e 17,5% em 2024-2025. Negociado com desconto 20%-22% vs histórico. PA R$32 para R$37 (upside 28%).",
    "https://www.infomoney.com.br/mercados/santander-brasil-sanb11-mostra-melhora-mas-ainda-tem-longo-caminho-a-percorrer-como-os-analistas-viram-o-balanco-do-2o-tri/":
        "Casas mantêm cautela apesar de melhora no 2T23. XP neutra com PA R$34. Citi venda: 'A formação de NPL ainda mostra o longo caminho a ser percorrido pelo banco para ajustar seu perfil de risco, com crescimento moderado dos empréstimos e contração sequencial do NIM'. BBI underperform com PA R$25 — não viu números com bons olhos.",

    # ABCB4
    "https://www.infomoney.com.br/mercados/abc-brasil-abcb4-ve-lucro-subir-a-r-232-mi-mas-analistas-veem-tendencias-mistas-e-acao-cai/":
        "BBI: 'ABC Brasil relatou tendências mistas no 4T23, NII começou a mostrar crescimento mais lento no segmento médio, terminando o ano abaixo do guidance'. Maior deterioração na inadimplência. BBA mantém marketperform: 'Recomendação dada perspectiva de fraco impulso operacional. Riscos descendentes para estimativas de provisões'.",
    "https://www.infomoney.com.br/mercados/abc-brasil-abcb4-mesmo-com-patrimonio-remunerado-pelo-cdi-banco-ve-juros-mais-baixos-como-vetor-de-crescimento/":
        "Queda dos juros deve destravar o plano de crescimento do banco. 'Essa estratégia só se beneficia de uma taxa de juros mais baixa'. BTG Pactual recomenda compra com PA R$25, 'grandes fãs do time de gestão' e enxergam 'sólidas vias de crescimento'. Guide vê valuation descontado.",
    "https://www.infomoney.com.br/onde-investir/small-caps-ou-blue-chips-dividendos-queda-selic/":
        "ABCB4 é a preferida dos analistas para os próximos meses entre small caps em setores perenes, DY projetado de até 8%. Abdouni (Levante): 'banco lucrativo, apresentou bons resultados nos últimos dez anos e negocia abaixo do valor patrimonial'. Serra (Toro): 'banco costuma ter inadimplência menor do que pares'.",

    # EGIE3
    "https://www.infomoney.com.br/mercados/engie-egie3-jpmorgan-nao-ve-potencial-de-valorizacao-e-corta-recomendacao-do-papel-para-venda/":
        "JPM corta para venda: TIR implícita apertada de 8,6% após desempenho superior. Necessidade de desalavancagem após Atlas (R$2,3bi) + R$6,8bi em capex — investimento total ultrapassará R$9bi em 2024. 'Mercado permanece pessimista em relação ao aumento da capacidade de energia renovável e penalizará empresas que aumentam investimentos'.",
    "https://www.infomoney.com.br/mercados/engie-egie3-esta-menos-atrativa-itau-bba-revisa-geradoras-e-corta-recomendacao/":
        "BBA rebaixa de compra para neutra com PA R$40,10. 'Papel negociado a TIR implícita de 8%, vs 5,7% dos títulos do Tesouro brasileiro, não muito atrativo'. Garantia física contratada até 2026. Capex relevante nos próximos 2 anos aumentará alavancagem; redução do payout de 100% para 55% — DY estimado de 5%, perderá apelo.",
    "https://www.infomoney.com.br/onde-investir/acoes-recomendadas-dividendos-maio-2023/":
        "Engie assumiu liderança entre ações mais indicadas para dividendos, desbancando Vale após 12 meses. Mantém 6 recomendações. Terra: 'avanço de projetos de transmissão e novos contratos de venda de energia (142 MW médios entre 2022-2027)'. XP: 'grupo possui uma das melhores estratégias de comercialização do país, sólida geração de caixa'.",

    # EQTL3
    "https://www.infomoney.com.br/mercados/equatorial-eqtl3-nao-ve-retorno-atraente-nos-proximos-leiloes-de-transmissao/":
        "Resultados do 4T21 sólidos, impulsionados por crescimento de volumes e melhor eficiência em custos, inadimplência abaixo do previsto. Credit Suisse: 'Equatorial continua marcando território como uma das favoritas nas conversas com clientes, dado que oferece uma história de diversificação, crescimento e qualidade'.",
    "https://www.infomoney.com.br/mercados/equatorial-eqtl3-salta-apos-ser-unica-a-entregar-oferta-por-sabesp-sbsp3-tem-queda/":
        "Genial: 'A verdadeira apreensão do acionista deve estar no risco de eventualmente a operação não ser concluída por falta de demanda. A Equatorial é um dos players com excelente track-record na gestão de concessões de serviço público e achamos sua permanência na operação como positiva para o case'. Ação saltou 6,29%.",

    # CPFE3
    "https://www.infomoney.com.br/onde-investir/8-acoes-de-dividendos-indicadas-para-julho-cpfe3-estreia-entre-os-destaques/":
        "CPFE3 estreia entre destaques de dividendos com 4 recomendações. BTG Pactual: 'CPFE3 negociada a TIR real de 10,2%, ao mesmo tempo em que entregou fortes resultados operacionais que permitiram volumes expressivos de dividendos. CPFL distribuiu payout de 100% nos últimos dois anos, fundamental para o excelente desempenho das ações em 2022'.",

    # TAEE11
    "https://www.infomoney.com.br/mercados/taesa-taee11-busca-equilibrio-dividendos-crescimento-alavancagem-acoes-caem-balanco/":
        "MS mantém underweight com PA R$35: 'ação pouco atraente em relação aos concorrentes, embora dividendos estejam atualmente acima dos pares'. BBA underperform com PA R$35,95: 4T22 neutros, Ebitda 7% abaixo, 'projetamos aumento da alavancagem para os próximos anos (>4x), dado o grande capex esperado dos projetos em construção'.",
    "https://www.infomoney.com.br/mercados/alupar-alup11-isa-cteep-trpl4-e-taesa-taee11-pagam-bons-dividendos-mas-por-que-a-xp-nao-recomenda-compra-para-as-acoes/":
        "XP mantém neutra com PA R$26: Taesa negocia a TIR real alavancada de 6,2% vs 7,1% dos pares e em linha com NTN-B. 'Embora considere a Taesa empresa de alta qualidade, defensiva e de baixo beta devido aos fluxos de caixa previsíveis, a XP acredita que essa chamada já se concretizou'.",
    "https://www.infomoney.com.br/onde-investir/dividendos-de-energia-taee11-trpl4-ou-alup11-veja-quanto-r-5-mil-rendem-nelas/":
        "Rossetti (Melver): 'Olhando à frente, a companhia está em estágio mais maduro do que as outras. Algumas concessões vencem primeiro e a gestão não está tão ativa nos leilões recentes. A explicação é a alavancagem, que está em 3,7x dívida líquida/Ebitda, a maior dentre as três'. Volume de pagamentos pode diminuir; ISA CTEEP mais promissora.",

    # CMIG4
    "https://www.infomoney.com.br/mercados/cemig-cmig4-da-privatizacao-a-federalizacao-tese-para-acoes-tem-forte-virada-e-traz-duvidas-no-mercado-o-que-esperar/":
        "BBI neutra com PA R$13: 'Caso a Cemig seja federalizada, estima uma queda para uma TIR real de pelo menos 15% a 17%, implicando um preço de R$8,90/ação a R$7,50/ação. Negociada na casa dos R$11,30, a ação ainda teria espaço para baixa entre 21% e 33%'. Genial mantém manutenção dado cenário de volatilidade.",
    "https://www.infomoney.com.br/mercados/jpmorgan-eleva-cemig-cmig4-e-camil-caml3-compra-rebaixa-alupar-alup11-e-mantem-marcopolo-pomo4-top-pick-acoes-reagem/":
        "JPM eleva CMIG4 para compra: 'utilities estatais controladas por Minas Gerais estão sendo mal avaliadas pelo mercado'. Cemig com bons resultados, capex de crescimento com retornos atrativos, avaliação atraente. TIR implícita de 12,2% (vs setor 11,6%), 5x EV/Ebitda. PA R$16, upside 29%, retorno total 42%.",
    "https://www.infomoney.com.br/mercados/cemig-cmig4-cai-mais-de-10-com-noticia-de-que-governo-de-mg-aceitou-repassar-ativos-para-abater-divida-com-uniao/":
        "Notícia de federalização derruba ação 9,71% para R$11,35. 'Dado o caminho desafiador da federalização, não entraríamos em pânico com esta notícia. No entanto, não compraríamos a Cemig com a fraqueza dos papéis, pois poderá haver mais fluxo de notícias políticas nas próximas semanas'. BBA: difícil encontrar conforto em ponto de entrada.",
}


def main() -> None:
    triage_rows = []
    with TRIAGE_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            triage_rows.append(r)

    keep = [r for r in triage_rows if r["triage_recommendation"] == "KEEP"]

    candidates_by_url = {}
    for tkr in COMPANY_NAMES:
        for c in load_candidates(tkr):
            candidates_by_url[c["url"]] = c

    curated = []
    missing_rationale = []
    for r in keep:
        url = r["url"]
        rationale = RATIONALES.get(url)
        if rationale is None:
            missing_rationale.append(url)
            continue
        curated.append({
            "url": url,
            "ticker": r["ticker"],
            "published_date": r["published_date"],
            "direction": r["direction"],
            "drivers": [d for d in r["drivers_mentioned"].split("|") if d],
            "rationale": clip_rationale(rationale),
        })

    save_curated(curated)
    print(f"KEEP rows: {len(keep)}")
    print(f"Curated theses: {len(curated)}")
    print(f"Missing rationales: {len(missing_rationale)}")
    for u in missing_rationale:
        print(f"  - {u}")


if __name__ == "__main__":
    main()
