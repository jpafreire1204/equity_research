"""One-off: persist Exa-discovered candidates as data/validation/candidates_{ticker}.json.

The MCP tools are only callable from the Claude Code session; this script bundles the
articles that were retrieved during discovery so they can be loaded by triage/extraction.
"""
from __future__ import annotations

from src.validation.discovery import save_candidates, dedupe, filter_candidates


def C(url, ticker, title, date, author, text, q="combined"):
    return {
        "url": url, "ticker": ticker, "title": title,
        "published_date": date, "author": author,
        "full_text": text, "source_query": q,
    }


ITUB4 = [
    C("https://www.infomoney.com.br/mercados/por-que-o-itau-itub4-e-a-acao-preferida-da-xp-no-setor-bancario/",
      "ITUB4", "Por que o Itaú (ITUB4) é a ação preferida da XP no setor bancário",
      "2023-09-27", "Felipe Moreira",
      "A XP Investimentos reiterou recomendação de compra para ações do Itaú Unibanco (ITUB4), com novo preço-alvo "
      "para 2024 de R$35 (potencial de alta de 32%). A equipe espera que o banco se beneficie do ciclo de afrouxamento "
      "monetário, que reduzirá custo do financiamento mais rapidamente do que juros dos empréstimos. Maior apetite por "
      "crédito impulsionando crescimento mais forte da carteira no 2S23, combinado com menor custo do crédito e NPL "
      "abaixo da média do SFN, deverá sustentar dinâmica positiva dos lucros do Itaú. Índices de capital saudáveis "
      "abrem espaço para payout mais alto. Itaú negocia com 6,8x P/L e 1,3x P/VPA, abaixo dos múltiplos históricos de "
      "7,9x e 1,6x — desconto exagerado, na visão da XP."),

    C("https://www.infomoney.com.br/mercados/itau-unibanco-itub4-tem-recomendacao-elevada-a-compra-com-avaliacao-atraente/",
      "ITUB4", "Itaú Unibanco (ITUB4) tem recomendação elevada à compra, com avaliação atraente",
      "2023-09-15", "Felipe Moreira",
      "Bradesco BBI elevou recomendação de ITUB4 de neutro para outperform, com preço-alvo de R$36 (de R$29), upside "
      "de 30%. Itaú oferece relação risco-recompensa atraente, principais riscos já precificados. Pode continuar "
      "apresentando forte crescimento de lucros e ROE superior. Balanço forte, com elevado índice de cobertura e base "
      "de capital, apoiando crescimento sólido dos empréstimos e/ou payout mais elevado. Itaú negociado com avaliação "
      "atrativa e margem de segurança significativa, oferece o melhor risco/recompensa entre bancos brasileiros. "
      "Projeções de lucro líquido elevadas em 5,3% para 2024 (R$40,1bi) e 8,5% para 2025 (R$45,1bi), com ROE de 20,5%."),

    C("https://www.infomoney.com.br/mercados/itau-itub4-acoes-resultado-banco-desponta-entre-pares-do-setor-mais-uma-vez-dizem-analistas/",
      "ITUB4", "Itaú (ITUB4): resultado do 2º tri faz banco despontar entre pares do setor mais uma vez",
      "2023-08-08", "Mitchel Diniz",
      "O resultado do Itaú no 2T23 foi positivo, reiterando a estratégia do banco de focar em clientes de baixo risco "
      "enquanto mantém crescimento de margens financeiras. Credit Suisse: Itaú mostrou consistência e capacidade de "
      "gerir custos, ROE de 21,5% no Brasil, qualidade de ativos sob controle e formação de inadimplência "
      "desacelerando. Morgan Stanley: outro trimestre consistente e sólido, mais pontos positivos do que negativos no "
      "balanço, desaceleração gradual nas concessões em linha com esperado e qualidade dos ativos estabilizada. "
      "Provisões de R$9,6bi (+6,7% T/T) com índice de cobertura saudável de 212%."),

    C("https://www.infomoney.com.br/onde-investir/itau-itub4-tem-espaco-para-dividendo-extraordinario-de-ate-r-14-bilhoes-avalia-xp/",
      "ITUB4", "Itaú (ITUB4) tem espaço para dividendo extraordinário de até R$ 14 bilhões, avalia XP",
      "2023-12-11", "Paulo Barros",
      "Itaú Unibanco tem espaço para distribuir dividendo extraordinário de até R$14 bilhões. Analistas da XP avaliam "
      "que o banco terá alívio em termos de exigência de capital em 2025, com Basileia faseada de 2025 a 2028. Com "
      "essa folga, o banco pode aumentar payout. Forte reputação como bom administrador de capital, histórico de "
      "pagamento robusto (74,7% médio entre 2017-2019). Se o pagamento extra se concretizar, payout sobe de 30% "
      "para 67,9%, dividend yield mais que dobra de ~4% para 9%. Estimativa de lucro de R$35,17 bilhões."),

    C("https://www.infomoney.com.br/mercados/as-acoes-do-itau-estao-caras-ou-baratas/",
      "ITUB4", "As ações do Itaú estão caras ou baratas?",
      "2024-05-31", "Camille Bocanegra",
      "Itaú segue como preferida do setor para muitos analistas, como o research da XP. Não é a mais barata pelos "
      "fundamentos: P/VPA de 1,79x (esperado <1x para barata) e P/L de 9,07x — não está nem entre as mais caras nem "
      "as mais baratas. Levante: 'Itaú negocia com múltiplos atrativos, mas não é tese de crescimento dado tamanho de "
      "mercado'. Dividend yield interessante de 8% torna a tese assimétrica. VG Research vê múltiplos abaixo da média "
      "histórica. Artigo apresenta visão equilibrada/balanced — sem direção forte do autor."),

    C("https://www.infomoney.com.br/mercados/itau-itub4-analistas-destacam-solidez-de-margens-financeiras-mas-apontam-queda-na-qualidade-de-ativos/",
      "ITUB4", "Itaú (ITUB4): analistas destacam solidez de margens, mas atenção para qualidade de ativos",
      "2022-08-09", "Mitchel Diniz",
      "Resultados do 2T22 vieram acima do esperado pelo consenso. Margens financeiras melhores que pares, mas com "
      "ressalva quanto à qualidade dos ativos em cartões de crédito e empréstimos pessoais. JP Morgan: 'Itaú se saiu "
      "melhor que pares na qualidade de ativos, taxa de inadimplência piorando apenas 10bp'. Bradesco BBI: melhores "
      "margens compensaram maior custo de risco; provisões mais altas poderiam acender luz amarela sobre qualidade dos "
      "ativos. BBI mantém outperform com preço-alvo R$32, justificando valuation atrativo, com ressalvas."),

    C("https://www.infomoney.com.br/mercados/bofa-eleva-acao-do-itau-itub4-para-compra-e-elenca-7-temas-para-os-bancos-em-2024/",
      "ITUB4", "BofA eleva ação do Itaú (ITUB4) para compra e elenca 7 temas para os bancos em 2024",
      "2024-01-17", "Lara Rizério",
      "Bank of America elevou recomendação para ITUB4 de neutro para compra. BofA elevou recomendação por considerar "
      "que o valuation premium é merecido dada execução superior, sendo uma das preferências ao lado de BPAC11. "
      "Preço-alvo elevado de R$33 para R$40, ou potencial de alta de 20%. 7 temas para bancos 2024: i) inadimplência "
      "atingindo o pico, ii) crescimento da carteira de empréstimos próximo de inflexão, iii) normalização gradual da "
      "margem financeira, iv) reclassificação dos ativos com múltiplos 30% abaixo do pré-pandemia, v) competição de "
      "neobancos mapeada, vi) menores incertezas regulatórias, vii) normalização da taxa efetiva de imposto."),

    C("https://www.infomoney.com.br/mercados/morgan-stanley-rebaixa-itau-itub4-e-elege-bradesco-bbdc4-como-favorito-entre-bancoes-de-olho-na-queda-da-selic/",
      "ITUB4", "Morgan Stanley rebaixa Itaú (ITUB4) e elege Bradesco como favorito entre bancões",
      "2023-05-19", "Equipe InfoMoney",
      "Morgan Stanley reduziu recomendação para ADRs do Itaú de overweight para equalweight, reduzindo preço-alvo de "
      "US$7,20 para US$6,80. 'Estamos rebaixando o Itaú dada a extensa evidência de baixo desempenho quando as taxas "
      "caem. Difícil ignorar resultados menos favoráveis do banco como reação à queda das taxas no passado'. Durante "
      "períodos de flexibilização, Itaú se destacou como ação com desempenho abaixo. ROE dos últimos 12 meses do banco "
      "também mostrou quedas mais acentuadas entre os quatro grandes quando as taxas caíram. Sensibilidade mais alta a "
      "queda de juros que pares."),

    C("https://www.infomoney.com.br/mercados/itau-itub4-morgan-eleva-adr-a-compra-com-selic-alta-valuation-e-bons-dividendos/",
      "ITUB4", "Itaú: a recomendação elevada pelo Morgan Stanley que fez ITUB4 ser destaque no pregão",
      "2024-06-17", "Lara Rizério",
      "Morgan Stanley elevou recomendação dos ADRs de equalweight para overweight, preço-alvo de US$7,50 para US$8 "
      "(potencial de alta de 38%). Selic mais alta por mais tempo, valuation atrativo, papel defensivo em piora "
      "macro/política e forte execução são fatores positivos. Recente liquidação proporciona ponto de entrada atrativo, "
      "ADRs corrigiram 17% no acumulado do ano. Execução de alto nível, aumento da eficiência de custos e retornos de "
      "capital atrativos. Itaú continua a liderar bancos tradicionais da região na transformação digital. Dividend "
      "yield de 7%."),

    C("https://www.infomoney.com.br/mercados/itub4-ou-bbdc4-analise-das-acoes-mostra-banco-mais-promissor/",
      "ITUB4", "ITUB4 ou BBDC4: Análise das ações mostra banco mais promissor",
      "2023-03-31", "Rodrigo Petry",
      "Análise técnica curtíssimo prazo. ITUB4 testou LTA, suporte e último fundo em R$22,30; com rompimento do último "
      "topo do gráfico diário em R$23,90, podemos esperar continuidade do movimento de alta no curtíssimo prazo. "
      "Análise técnica PagBank: ações buscam recuperação, podem buscar a região da média de 200 períodos em R$25,14. "
      "Conteúdo focado em análise técnica, sem tese fundamentalista clara."),
]

BBDC4 = [
    C("https://www.infomoney.com.br/mercados/bradesco-bbdc4-reietera-recomendacao-venda/",
      "BBDC4", "Bradesco (BBDC4): Itaú BBA não concorda com rali da ação e reitera recomendação equivalente à venda",
      "2023-06-01", "Felipe Moreira",
      "Itaú BBA reiterou visão pessimista com BBDC4 e manteve underperform com preço-alvo de R$15. Espera que a "
      "recuperação dos negócios fique abaixo de pares entre 2023 e 2024. 'Bradesco terá que lidar com safras ruins de "
      "crédito por mais tempo do que concorrentes, que já estão mais avançados em domar NPLs. Banco também tem menos "
      "espaço, em provisões e capital, para acelerar muito cedo'. Carteira deve crescer apenas 5% em 2023 e 8% em "
      "2024. Beneficios para NII apenas no 2S24. Bradesco tenta crescer via alta renda mas não pode mudar "
      "posicionamento da noite para o dia. Cobertura para risco baixa, posição de capital abaixo dos pares."),

    C("https://www.infomoney.com.br/mercados/bradesco-bbdc4-por-que-o-morgan-stanley-segue-otimista-indo-contra-a-cautela-geral-do-mercado/",
      "BBDC4", "Bradesco (BBDC4): por que o Morgan segue otimista, indo contra a cautela geral do mercado",
      "2024-02-12", "Lara Rizério",
      "Morgan Stanley manteve overweight para BBDC4. Após reunião com novo presidente Marcelo Noronha, MS saiu mais "
      "confiante de que recuperação do ROE 'poderá ocorrer mais cedo do que mais tarde'. Foco em digitalização e "
      "racionalização da abrangência do banco como principais catalisadores para redução de custos. Migração para "
      "nuvem termina em 2025. Outros bancos cautelosos: Goldman Sachs com venda, Itaú BBA com neutro e preço-alvo "
      "R$15,50. ROE de 11% e 14% para 2024 e 2025 nas estimativas BBA. De 14 casas LSEG, 10 neutras, 1 venda, 3 compra."),

    C("https://www.infomoney.com.br/mercados/bradesco-bbdc4-desempenho-acoes-resultado-fraco-e-comprova-que-recuperacao-da-rentabilidade-sera-lenta-apontam-analistas/",
      "BBDC4", "Bradesco (BBDC4): de números decepcionantes à recuperação adiada",
      "2023-08-04", "Mitchel Diniz",
      "Resultados do 2T23 mostram Bradesco com dificuldades para crescer e rentabilizar carteira de crédito, "
      "inadimplência elevada. Conclusão praticamente unânime entre analistas. Ações BBDC4 caíram 6,65% para R$15,45. "
      "XP: 'Acreditamos numa curva de melhoria, mas vemos o ponto de inflexão um pouco mais distante'. Bradesco "
      "revisou para baixo guidance 2023, expansão da carteira foi reduzida de 6,5-9,5% para 1-5%. Genial: Bradesco foi "
      "'salvo pelo seguro' no 2T23, lucro fraco. Margem financeira fraca pois Bradesco tornou restrição de crédito "
      "mais restrita."),

    C("https://www.infomoney.com.br/mercados/bradesco-bbdc4-tem-resultado-fraco-mas-superando-projecoes-desempenho-acoes-como-os-numeros-do-1o-tri-reacendem-o-debate-sobre-os-ativos/",
      "BBDC4", "Bradesco (BBDC4): resultado é fraco, mas supera projeções",
      "2023-05-05", "Lara Rizério",
      "Resultados do 1T23 trazem risco negativo para estimativas de 2023, com receitas e despesas com provisões "
      "seguindo pressionadas. Lucro de R$4,3bi foi 37% menor que 1T22 e ROE bem abaixo de rivais. Provisões altas, "
      "carteira contraiu 2,2% no trimestre, margem financeira enfraqueceu 2,4% YoY. Casa mantém underperform. Morgan "
      "Stanley mais otimista: lucro pode ser surpresa positiva, especialmente em provisões para inadimplência. Casa "
      "MS overweight. De 17 casas Refinitiv: 5 compra, 8 manutenção, 4 venda, preço-alvo R$16,54 (upside 17,56%)."),

    C("https://www.infomoney.com.br/mercados/bradesco-bbdc4-acao-queda-alem-de-americanas-numeros-fracos-4o-tri-projecoes-ruins-2023-analistas-reforcam-pessimismo/",
      "BBDC4", "Ação do Bradesco (BBDC4) fecha em queda de mais de 8% após balanço",
      "2023-02-10", "Lara Rizério",
      "XP: apesar de 2022 já ter sido fortemente afetado pelo aumento da inadimplência, espera-se que resultados "
      "continuem pressionados nos próximos trimestres devido ao ambiente macro desafiador. Itaú BBA: projeções "
      "indicam que desafios continuarão, com NII total a crescer 10% YoY vs despesas de provisão crescendo até 20%. "
      "BBA estima R$20bi de lucro líquido (ROE de 12%), abaixo de R$25bi do mercado. NII fraco e provisões altas devem "
      "manter ROEs abaixo do custo de capital em 2023 e 2024. BBA reiterou underperform, levará tempo para Bradesco "
      "recuperar dos múltiplos atuais de 0,9x P/VPA. Citi: 'as coisas continuam piorando', preço-alvo R$19, neutra."),

    C("https://www.infomoney.com.br/mercados/itau-bba-corta-acao-bradesco-bbdc4-para-venda-ve-tempestade-perfeita-para-lucros-entre-2023-e-2024-e-alerta-para-efeito-americanas/",
      "BBDC4", "Itaú BBA corta Bradesco (BBDC4) para venda, vê tempestade perfeita para lucros entre 2023 e 2024",
      "2023-01-30", "Lara Rizério",
      "Itaú BBA cortou recomendação de BBDC4 de marketperform para underperform. 'Vemos uma tempestade perfeita para os "
      "lucros de 2023-2024. Carteira de empréstimos crescerá menos, NIMs enfraquecerão e custos de crédito subirão.' "
      "BBA reduziu estimativas, NII fraca e despesas altas com provisões devem levar a ROE abaixo do custo de capital. "
      "Lucro líquido projetado de R$20,4bi para 2023 e R$24bi para 2024 (ROE 13% e 14%). Genial Investimentos cortou "
      "manutenção para venda, citando absorção de perdas com Americanas e ciclo de inadimplência."),

    C("https://www.infomoney.com.br/mercados/apos-jp-bradesco-bbdc4-tem-recomendacao-cortada-pelo-itau-bba-com-deterioracao-da-qualidade-do-credito/",
      "BBDC4", "Bradesco (BBDC4) tem recomendação cortada pelo Itaú BBA, com deterioração da qualidade do crédito",
      "2022-10-10", "Felipe Moreira",
      "Itaú BBA cortou BBDC4 de outperform para market perform. Preço-alvo de R$23 para R$21 ao final de 2023, upside "
      "de apenas 2,6%. Reclassificação em função da deterioração da qualidade do crédito e da margem financeira. "
      "BBA projeta resultados fracos no 3T22, índices de inadimplência de varejo em alta e contaminação da carteira "
      "PME. Com possível desaceleração econômica, há preocupações com inadimplência corporativa em 2023. BBA reduziu "
      "previsões de lucros em 4% e 10% para 2022/2023. 'Qualquer reclassificação dos múltiplos teria de vir de fatores "
      "exógenos como risco-país'."),

    C("https://www.infomoney.com.br/mercados/credit-suisse-rebaixa-banco-do-brasil-bbas3-eleva-bradesco-bbdc4-e-mantem-itau-itub4-como-top-pick-entre-bancoes-de-olho-selic/",
      "BBDC4", "Credit eleva Bradesco (BBDC4)",
      "2023-06-05", "Lara Rizério",
      "Credit Suisse elevou Bradesco de underperform para neutra, preço-alvo de R$15 para R$18 (upside de 12%). Banco "
      "suíço vê valuation mais justo, principalmente com taxa livre de risco mais baixa. 'Continuamos a ver os riscos "
      "para os ganhos mais altos versus o Itaú (principalmente relacionado à qualidade dos ativos), e esperamos que o "
      "ROE do Bradesco fique em linha com o custo de capital apenas em 2025 (ROE de 15,8%)'. Múltiplos dos dois bancos "
      "alinhados em P/L 2024 de 6,5x, o que apoia preferência pelo Itaú dado menor risco."),
]

BBAS3 = [
    C("https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-apos-recorde-em-2023-ate-onde-acao-da-estatal-pode-ir-neste-ano/",
      "BBAS3", "Banco do Brasil (BBAS3): após recorde em 2023, até onde ação da estatal pode ir neste ano?",
      "2024-01-15", "Lara Rizério",
      "Genial recomenda compra com preço-alvo R$64,90. 'Antecipamos outro trimestre positivo para BB, projetamos um "
      "2024 sem grandes surpresas, mantendo consistência'. Lucro 2023 projetado em R$35bi (ponto médio do guidance), "
      "ROE de 20,7%. 'Esse desempenho supera significativamente vários bancos privados'. Cenário 'modesto' para 2024 "
      "leva a recomendação neutra para algumas casas. BBI cortou de compra para neutra. Safra cortou em novembro, "
      "destacando que lucro e retorno teriam atingido pico. Estimativa de lucro de R$37bi para 2024."),

    C("https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-balanco-nao-foi-tao-bom-quanto-parece-mas-guidance-e-dividendos-guiam-animo-desempenho-acoes/",
      "BBAS3", "BB divulga lucro recorde, eleva payout e projeta bom 2024",
      "2024-02-09", "Lara Rizério",
      "Lucro líquido ajustado de 2024 deve ficar entre R$37-40bi. Genial: 'guidance aponta para mais um ano de lucro "
      "robusto. ROE deve se manter próximo de 21%, competindo com Itaú em rentabilidade'. BB anunciou pagamento de "
      "dividendos e JCP de R$2,38bi e aumento de payout de 40% para 45% (DY de 10% projetado pelo BBI). Citi: 'mercado "
      "deve receber bem visão positiva reiterada pelo BB, levando a elevação de estimativas de consenso. Payout mais "
      "alto era requisição recorrente dos investidores, deve levar a reclassificação dos ativos.' Citi recomenda "
      "compra, preço-alvo R$74."),

    C("https://www.infomoney.com.br/onde-investir/como-serao-os-dividendos-de-bbas3-sob-a-gestao-de-tarciana-medeiros-mercado-projeta-taxas-de-ate-137/",
      "BBAS3", "Como serão os dividendos de BBAS3 sob a gestão de Tarciana Medeiros?",
      "2023-01-10", "Katherine Rivas",
      "Dos seis analistas e um gestor consultados pelo InfoMoney, quatro recomendam compra para 2023. DY estimado de "
      "6,4% a 13,7%. Rabelo (VG): 'apesar das sinalizações negativas do governo, continuamos a indicar compra'. "
      "Tahara (Benndorf) recomenda compra, DY 13%, preço-alvo R$59. 'Banco negocia próximo das mínimas em P/VP, mesmo "
      "com resultados históricos. Risco de governança menor que 2014-2015'. Reis (Suno) recomenda compra, DY 10-12%. "
      "Nigri (Dica de Hoje) cenário base DY 10,8%, lucro R$27bi. Ativa cautelosa, DY 13,7% mas não recomenda compra."),

    C("https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-acoes-estao-caras-ou-baratas/",
      "BBAS3", "As ações do Banco do Brasil estão caras?",
      "2024-05-29", "Camille Bocanegra",
      "BB negocia com P/L abaixo dos pares, a 4,47x. Pelo P/VPA, BB tem 0,88x — papel pode ser considerado barato. BB "
      "tem diferencial de bom pagador de dividendos, DY próximo de 10%-12%. Rabelo (VG Research) acredita que papéis "
      "seguem descontados, risco político antecipado desde 2022 não se materializou. Nascimento (Levante): atratividade "
      "da tese seria avanço nas linhas de crédito (consignado e agro) e assimetria. 'Boa presença de retorno em "
      "dividendos torna o papel ainda mais atrativo'."),

    C("https://www.infomoney.com.br/mercados/banco-do-brasil-bbas3-e-mais-uma-vez-o-campeao-de-lucro-e-roe-entre-os-bancoes-o-que-esperar-para-a-acao/",
      "BBAS3", "Banco do Brasil (BBAS3) é mais uma vez o campeão de lucro e ROE entre os bancões",
      "2023-08-10", "Lara Rizério, Mitchel Diniz",
      "BBA: crescimento da receita do BB de 6% no trimestre, maior entre grandes bancos, NII subindo 8% e serviços +2%. "
      "'Esperamos que ações permaneçam positivas, negociando a 0,7x P/B e 3,4x P/L em 2024'. BBA tem compra para BBAS3, "
      "preço-alvo R$56. Genial reitera comprar, preço-alvo R$62,80, vendo múltiplos do banco estatal como atrativos. "
      "Ainda muito descontado depois de subir 41% YTD. BBI mais conservador, neutro, preço-alvo R$48. 'Mantemos visão "
      "de que lucros do banco atingiram o pico'."),

    C("https://www.infomoney.com.br/mercados/bb-bbas3-seguira-com-rentabilidade-alta-como-os-analistas-veem-a-estrategia-do-banco/",
      "BBAS3", "BB (BBAS3) seguirá com rentabilidade alta? Como analistas veem a estratégia",
      "2024-03-05", "Ana Paula Ribeiro",
      "Estratégia de crédito do BB ajudará a manter rentabilidade acima de 20%. Genial: 'BB deve continuar entregando "
      "boa rentabilidade (ROE 21%) em 2024, com condições de replicar nos anos subsequentes'. ROE em crescente: era "
      "<10% em 2016. Carteira de crédito equilibrada (agro, PF, empresas com 1/3 cada). XP também vê manutenção do ROE "
      "do BB acima de 20% em 2024. XP manteve compra e elevou preço-alvo de R$61 para R$73 (upside 26%). 'Apesar de "
      "visão positiva, ainda vê como difícil identificar gatilhos potenciais de curto prazo para múltiplos descontados'."),

    C("https://www.infomoney.com.br/mercados/por-que-as-acoes-do-banco-do-brasil-bbas3-estao-entre-as-preferidas-do-itau-bba-para-2024/",
      "BBAS3", "Por que as ações do Banco do Brasil (BBAS3) estão entre as preferidas do Itaú BBA para 2024",
      "2024-01-17", "Reuters",
      "Itaú BBA reiterou outperform para BBAS3 e elevou preço-alvo de R$59 para R$65. 'BB oferece valor, crescimento e "
      "forte rendimento de dividendo de 12%'. 'Após 2023 já forte, esperamos crescimento de 9% na receita YoY e 10% no "
      "lucro líquido, gerando outro ROE acima do setor de 21%'. Apesar do rali de 76% em 2023, ações permanecem com "
      "desconto, negociadas a 0,8x P/VPA e 4x P/L. 'Em cada trimestre sucessivo em que lucros se expandem, BB obtém "
      "revisões para cima e re-rates a partir de desconto cada vez menos justificado'. BB entre top picks do ano."),

    C("https://www.infomoney.com.br/onde-investir/dividendos-bancos-baratos-bbas3-sanb11-bbdc4-itub4/",
      "BBAS3", "Ações de bancos estão baratas para quem está à caça de dividendos?",
      "2023-05-19", "Katherine Rivas",
      "Banco do Brasil é apontado como melhor alternativa do setor para dividendos em 2023 — DY projetado de 11%. P/L "
      "projetado para 2023 de 3,44x (média 5y de 6,9x), DY de 12,17% nos últimos 12 meses, situação 'barata'. "
      "Recomendam compra: Benndorf, Ticker, GuiaInvest, VG Research, L4 Capital — preço-teto R$41,50 a R$52. "
      "Sobreira: poder de lucro projetado de 29,08% para 2023."),
]

SANB11 = [
    C("https://www.infomoney.com.br/mercados/santander-bbi-eleva-sanb11-de-venda-a-compra-tempos-ruins-nao-duram-para-sempre/",
      "SANB11", "Santander: BBI eleva SANB11 de venda a compra; tempos ruins não duram para sempre",
      "2024-05-03", "Felipe Moreira",
      "Bradesco BBI elevou SANB11 de venda para compra. Elevação impulsionada por perspectiva de maior rentabilidade e "
      "avaliação atrativa, após tendências positivas no balanço do 1T24. BBI prevê combinação benigna de crescimento "
      "mais rápido dos empréstimos, portfólio mais adequado, maiores ganhos comerciais e menor custo do risco. "
      "Santander empreendeu limpeza dolorosa mas necessária do balanço em 2022 e 2023. Estimativas de lucro líquido "
      "elevadas em 5,8% para R$14,0bi em 2024 e 8,0% para R$16,9bi em 2025. ROE de 16% e 17,5% em 2024/2025. Banco "
      "negociado com desconto de 20%-22% em relação à média histórica. Preço-alvo de R$32 para R$37 (upside 28%)."),

    C("https://www.infomoney.com.br/mercados/santander-brasil-sanb11-mostra-melhora-mas-ainda-tem-longo-caminho-a-percorrer-como-os-analistas-viram-o-balanco-do-2o-tri/",
      "SANB11", "Santander Brasil (SANB11) mostra melhora, mas ainda tem longo caminho a percorrer",
      "2023-07-26", "Lara Rizério, Mitchel Diniz",
      "XP: 'No geral, embora ainda pressionados por provisões mais altas e ajudados pelo imposto de renda positivo, "
      "vemos a combinação de balanço saudável com NII melhorada como indicadores antecedentes para melhores resultados "
      "no futuro'. Reiteram visão conservadora, neutra com preço-alvo R$34. Citi mantém venda — resultados confirmam "
      "visão negativa. NIM caindo 20bp, aumento de inadimplência. BBI underperform, preço-alvo R$25 — não viu números "
      "com bons olhos. 'Formação de NPL ainda mostra longo caminho para ajustar perfil de risco'."),

    C("https://www.infomoney.com.br/mercados/santander-brasil-sanb11-mostra-a-tao-esperada-recuperacao-da-qualidade-dos-ativos-no-3o-tri-com-queda-da-inadimplencia-desempenho-acoes/",
      "SANB11", "Santander Brasil (SANB11) mostra sinais de recuperação no 3º tri",
      "2023-10-25", "Lara Rizério",
      "XP: Santander apresentou resultados positivos e acima do esperado, recuperação saudável de rentabilidade. "
      "Tendência geral de recuperação em vários segmentos, melhoria no ROE. ROAE de 13,1% (vs 13,2% esperado). BBI "
      "também viu tendências melhores, com destaque para melhoras do índice de inadimplência. Genial: rentabilidade "
      "de apenas 13,1% continua fraca, mas resultado mostra sinais de melhora mais expressiva, consolidando "
      "trajetória de melhora gradual. CEO Mario Leão sinalizou caminho para ROE 15-20%. BBI underperform, Goldman "
      "venda, XP neutra — analistas seguem cautelosos."),

    C("https://www.infomoney.com.br/mercados/acoes-xp-ve-2023-desafiador-para-bancos-destaca-itau-itub4-como-preferido-e-eleva-santander-sanb11-a-neutro/",
      "SANB11", "XP vê 2023 desafiador para bancos, eleva Santander (SANB11) para neutro",
      "2022-12-27", "Felipe Moreira",
      "Santander foi o primeiro grande banco a assumir abordagem mais conservadora na concessão de crédito no final de "
      "2021 e analistas esperam que mantenha estratégia em 2023, com perspectivas macroeconômicas desafiadoras no "
      "curto prazo. No lado de valuation, após desempenho de preço mais fraco vs pares (+0,6% no ano vs +16,0% da "
      "média dos pares), XP vê assimetria negativa anterior como ajustada e ação com preço justo. XP elevou de venda "
      "para neutra, preço-alvo R$34 (upside 20%). 'Margem financeira de mercado deve seguir pressionada no 4T22 e em "
      "2023 pelos juros'."),
]

ABCB4 = [
    C("https://www.infomoney.com.br/mercados/abc-brasil-abcb4-ve-lucro-subir-a-r-232-mi-mas-analistas-veem-tendencias-mistas-e-acao-cai/",
      "ABCB4", "ABC Brasil vê lucro subir a R$ 232 mi, mas analistas veem tendências mistas",
      "2024-02-06", "Equipe InfoMoney",
      "BBI: 'ABC Brasil relatou tendências mistas no 4T23, à medida que NII começou a mostrar crescimento mais lento "
      "no segmento médio, terminando o ano abaixo do guidance (em 2,5%), enquanto cortes nas taxas de juros impactaram "
      "remuneração de capital, levando a compressão significativa nos NIMs'. Banco vê maior deterioração na "
      "inadimplência no segmento médio. BBI tem neutra para ABCB4 com preço-alvo R$26, mesma recomendação do BBA. "
      "BBA: 'Recomendação dada perspectiva de fraco impulso operacional. Vemos riscos descendentes para estimativas "
      "sobre provisões e eficiência, enquanto avaliações atuais provavelmente estão precificando ROE acima do nosso "
      "cenário base'."),

    C("https://www.infomoney.com.br/mercados/abc-brasil-abcb4-mesmo-com-patrimonio-remunerado-pelo-cdi-banco-ve-juros-mais-baixos-como-vetor-de-crescimento/",
      "ABCB4", "ABC Brasil (ABCB4): banco vê juros mais baixos como vetor de crescimento",
      "2023-07-18", "Mitchel Diniz",
      "Queda dos juros deve destravar o plano de crescimento do banco. 'Essa estratégia só se beneficia de uma taxa de "
      "juros mais baixa', diz Lulia. Guide incluiu papéis em carteira recomendada de dividendos, valuation descontado "
      "e deve se beneficiar com corte de juros. 'Maior apetite por risco, expectativas de alívio no endividamento e "
      "maior atividade na vertifical de mercado de capitais devem favorecer banco'. BTG Pactual recomendação compra, "
      "preço-alvo R$25, 'grandes fãs do time de gestão' e 'sólidas vias de crescimento'. JP Morgan neutra, preço-alvo "
      "R$24, 'estratégia certa, ao focar em grandes e médias empresas'."),

    C("https://www.infomoney.com.br/onde-investir/small-caps-ou-blue-chips-dividendos-queda-selic/",
      "ABCB4", "ABC Brasil (ABCB4) se destaca diante da queda da Selic",
      "2023-08-08", "Katherine Rivas",
      "ABC Brasil é a preferida dos analistas para os próximos meses entre small caps em setores perenes, com DY "
      "projetado de até 8%. ABCB4 está nas recomendações da Órama, Levante, Ticker Research e Toro Investimentos. "
      "Joao Abdouni (Levante): 'ABC é banco lucrativo, apresentou bons resultados nos últimos 10 anos e negocia abaixo "
      "do valor patrimonial'. Serra (Toro): 'Banco costuma ter inadimplência menor do que pares, faz com que tenha "
      "PDDs menores'. Com queda de juros deve ocorrer maior demanda de crédito por parte das empresas. 'DY de 8,39% "
      "atual deve permanecer ou ter leve aumento'."),

    C("https://www.infomoney.com.br/onde-investir/banco-abc-brasil-abcb4-reforma-dividendos-fim-jcp/",
      "ABCB4", "ABC Brasil tenta compensar possível fim do JCP com retorno maior",
      "2023-08-12", "Katherine Rivas",
      "Possível fim do JCP seria aplicado apenas em 2024, ABC teria mais tempo para aumentar rentabilidade. ROAE 2T23 "
      "foi de 15,1%. Cenário atual melhor que pandemia (13%). ABC Brasil cortou guidance de carteira de crédito de 12-"
      "16% para 4-8% em 2023, segmento middle de 35-45% para 5-15%. Executivo otimista com 2S23, deve beneficiar "
      "principalmente segmento middle com spreads maiores. 'Historicamente 2S é mais dinâmico, soma-se ao novo ciclo "
      "de corte de juros'."),
]

EGIE3 = [
    C("https://www.infomoney.com.br/mercados/engie-egie3-jpmorgan-nao-ve-potencial-de-valorizacao-e-corta-recomendacao-do-papel-para-venda/",
      "EGIE3", "Engie (EGIE3): JPMorgan não vê potencial de valorização e corta para venda",
      "2023-12-19", "Felipe Moreira",
      "JPMorgan cortou recomendação de neutro para venda, não vê potencial de valorização com base no preço-alvo de "
      "R$44. TIR implícita apertada de 8,6% após desempenho superior. Necessidade de desalavancagem da empresa após "
      "compra da Atlas Energy (R$2,3bi) e R$6,8bi em capex — investimento total 2024 ultrapassará R$9bi. Engie deve "
      "atingir 3,5x Dívida Líquida/Ebitda até final de 2024. 'Mercado permanece pessimista em relação ao aumento da "
      "capacidade de energia renovável e penalizará empresas que aumentam investimentos enquanto preços de energia "
      "permanecem baixos'. Engie estaria melhor com pagamento de proventos maior."),

    C("https://www.infomoney.com.br/mercados/engie-egie3-esta-menos-atrativa-itau-bba-revisa-geradoras-e-corta-recomendacao/",
      "EGIE3", "Engie (EGIE3) está menos atrativa? Itaú BBA corta recomendação",
      "2024-03-06", "Equipe InfoMoney",
      "Itaú BBA rebaixou EGIE3 de compra para neutra, preço-alvo R$40,10. 'Papel negociado a TIR implícita de 8%, vs "
      "5,7% para títulos do Tesouro brasileiro, não muito atrativo'. Garantia física majoritariamente contratada até "
      "2026, fica mais descontratada a partir de 2027. 'Engie é menos sensível a mudanças nos preços de energia de "
      "longo prazo, possui ativos de transmissão e transporte de gás. Não vemos catalisadores de curto prazo'. Capex "
      "relevante nos próximos 2 anos ocasionará aumento na alavancagem. Redução do payout de 100% para 55% (mínimo). "
      "DY estimado em 5%. 'Engie poderá perder apelo para investidores focados em dividendos'."),

    C("https://www.infomoney.com.br/onde-investir/acoes-recomendadas-dividendos-maio-2023/",
      "EGIE3", "EGIE3 passa VALE3 e é nova quase unanimidade",
      "2023-05-04", "Márcio Anaya",
      "Engie assumiu liderança entre ações mais indicadas para dividendos, desbancando Vale. Maior produtora privada "
      "de energia se mantém em 6 portfólios. Terra Investimentos justifica visão positiva com avanço de projetos de "
      "transmissão e novos contratos de venda de energia (142 MW médios entre 2022-2027). XP: 'grupo possui uma das "
      "melhores estratégias de comercialização do país, sólida geração de caixa'. Embora estatuto determine dividendos "
      "não inferiores a 30% do lucro, empresa vem realizando pagamentos de no mínimo 55%."),

    C("https://www.infomoney.com.br/mercados/engie-brasil-egie3-reduziu-dividendos-para-nao-deixar-de-aproveitar-oportunidades-diz-cfo-acoes-caem-apos-balanco/",
      "EGIE3", "Engie Brasil (EGIE3) reduziu dividendos; ação cai 4,4% após balanço",
      "2023-08-09", "Equipe InfoMoney",
      "Engie reduziu distribuição de dividendos para manter balanço robusto e aproveitar oportunidades. Pagou 55% do "
      "lucro 1S23 (R$767,2mi), restante mantido em caixa. Ações caíram 4,42% para R$41,35. CFO: 'cautelosa com cenário "
      "para desenvolvimento de novos projetos de geração, dada conjuntura de preços baixos de energia'. Para BBI, "
      "outperform, preço-alvo R$46,10, 'empresa compartilhou atualização positiva, reduzindo volumes não contratados'. "
      "XP: resultados do 2T23 abaixo das expectativas, condições operacionais piores que esperado, neutra preço-alvo "
      "R$49."),
]

EQTL3 = [
    C("https://www.infomoney.com.br/mercados/enel-mais-perto-de-vender-a-coelce-coce3-quais-os-impactos-para-as-possiveis-compradoras-equatorial-eqtl3-e-cpfl-cpfe3/",
      "EQTL3", "Enel mais perto de vender a Coelce: impactos para Equatorial e CPFL",
      "2023-07-24", "Equipe InfoMoney",
      "BBI mantém neutra para EQTL3 e CPFE3. Equatorial e CPFL estão competindo pela Coelce. Para BBI, se Equatorial "
      "comprar a Coelce a 1,2x-1,3x EV/RAB, apesar do BBI ver agregação de valor limitada, investidores provavelmente "
      "considerariam positiva pelas sinergias regionais. 'Alta alavancagem seria problema para Equatorial resolver, "
      "oferta de ações pode ser necessária'. Se Equatorial não conseguir comprar, pode haver decepção, ação parece "
      "precificar este movimento de M&A. Preço-alvo BBI EQTL3 R$33."),

    C("https://www.infomoney.com.br/mercados/equatorial-eqtl3-nao-ve-retorno-atraente-nos-proximos-leiloes-de-transmissao/",
      "EQTL3", "Equatorial não vê retorno atraente em próximos leilões de transmissão",
      "2022-03-24", "Augusto Diniz",
      "Resultados do 4T21 sólidos, impulsionados por crescimento de volumes e melhor eficiência em custos, "
      "inadimplência abaixo do previsto. Credit Suisse: 'Equatorial continua marcando território como uma das "
      "favoritas nas conversas com clientes, dado que oferece história de diversificação, crescimento e qualidade'. "
      "CEO disse que companhia está disposta a olhar próximos leilões de transmissão, mas só com retorno atrativo. "
      "Empresa focada na execução do plano de negócios, integração da Echoenergia recém-adquirida por R$7bi."),

    C("https://www.infomoney.com.br/mercados/equatorial-eqtl3-salta-apos-ser-unica-a-entregar-oferta-por-sabesp-sbsp3-tem-queda/",
      "EQTL3", "Equatorial (EQTL3) salta 6,29% após ser única a entregar oferta por Sabesp",
      "2024-06-27", "Felipe Moreira",
      "Ação saltou 6,29% para R$30,93 após notícias da Reuters de que companhia foi a única a formalizar proposta pela "
      "posição de acionista de referência na privatização da Sabesp. Genial Investimentos: 'Equatorial é um dos players "
      "com excelente track-record na gestão de concessões de serviço público. Achamos sua permanência na operação como "
      "positiva para o case'. Aegea desistiu por cláusula de poison pill."),

    C("https://www.infomoney.com.br/mercados/equatorial-eqtl3-adquire-celg-d-distribuidora-de-energia-de-goias-por-um-valor-total-r-75-bilhoes/",
      "EQTL3", "Equatorial (EQTL3) adquire Celg-D por R$ 7,5 bilhões",
      "2022-09-23", "Equipe InfoMoney",
      "Equatorial fechou aquisição da Celg-D por R$7,5bi (R$5,7bi em dívidas + R$1,6bi pagamento). Celg-D atende 237 "
      "municípios em Goiás. Equatorial fez follow-on de R$2,8bi e tem >R$10bi em caixa. Concorrentes interessadas "
      "incluíam Energisa, CPFL, EDP e Neoenergia. Após um ano da compra anterior pela Enel, base de ativos regulatória "
      "de R$3bi e investimentos de R$5bi, mas dificuldades em cumprir metas regulatórias."),
]

CPFE3 = [
    C("https://www.infomoney.com.br/mercados/cpfl-cpfe3-resultado-quarto-trimestre-2023/",
      "CPFE3", "Lucro da CPFL (CPFE3) cai 3,5%, para R$ 1,3 bi no quarto trimestre",
      "2024-03-21", "Ana Paula Ribeiro",
      "Lucro líquido caiu 3,5% YoY para R$1,327bi no 4T23. Ebitda recuou 18,2% YoY para R$3,111bi. Receita líquida de "
      "R$10,540bi (-1,8% YoY), distribuição responde por 80,1% do total. PMSO subiu 135,2% YoY. Resultado financeiro "
      "negativo R$637mi (-52,8%). Dívida líquida R$23,9bi (+2,1% YoY). Alavancagem dívida líquida/Ebitda em 1,87x, "
      "estável vs 4T22. Reportagem informativa, sem tese clara."),

    C("https://www.infomoney.com.br/mercados/cpfl-cpfe3-resultados-terceiro-trimestre-2023/",
      "CPFE3", "CPFL (CPFE3) tem lucro líquido de R$ 1,31 bilhão no 3º tri",
      "2023-11-09", "Estadão Conteúdo",
      "Lucro de R$1,313bi no 3T23 (-7,5% YoY). Acumulado 9M23: R$4,21bi (+9,5% YoY). Ebitda do trimestre R$3,134bi "
      "(+5,6% YoY). Distribuição lucro R$603mi, geração R$600mi, transmissão R$120mi (-48,2%). Dívida líquida R$23,1bi, "
      "alavancagem 1,71x considerada confortável. CFO: alavancagem confortável, covenant de até 3,75x. Reportagem de "
      "balanço, sem tese."),

    C("https://www.infomoney.com.br/onde-investir/acoes-de-dividendos-mais-indicadas-para-julho-2024/",
      "CPFE3", "Ações de dividendos mais indicadas para julho; CPFL entra na lista das preferidas",
      "2024-07-04", "Wellington Carvalho",
      "CPFE3 entra como principal novidade entre dividendos para julho 2024 — DY de até 9,3% nos próximos três anos. "
      "5 recomendações. Peretti (Santander): 'resultado bruto cresceu quase 16% no 1T, sinaliza para boa distribuição "
      "de dividendos'. 'Esperamos que CPFL entregue forte DY de 9,3% nos próximos três anos'. NOTA: 2024-07-04 está "
      "fora da janela 2024-06-30 — será filtrado."),

    C("https://www.infomoney.com.br/mercados/cpfl-cpfe3-resultados-primeiro-trimestre-2024/",
      "CPFE3", "CPFL (CPFE3) tem lucro de R$ 1,75 bilhão no 1º tri, alta anual de 6,3%",
      "2024-05-09", "Reuters",
      "Lucro líquido de R$1,75bi no 1T24 (+6,3% YoY), puxado por melhor desempenho das distribuidoras. Ebitda recorde "
      "de R$3,86bi (+9,5% YoY). Concessionárias viram crescimento de 5,1% da carga de energia. Crescimento de dois "
      "dígitos em residencial e comercial. CEO: altas temperaturas e mudança estrutural de hábitos de consumo. "
      "Indústria +2,2%, sinais de recuperação. Reportagem de balanço, sem tese clara."),

    C("https://www.infomoney.com.br/onde-investir/8-acoes-de-dividendos-indicadas-para-julho-cpfe3-estreia-entre-os-destaques/",
      "CPFE3", "8 ações de dividendos indicadas para julho 2023; CPFE3 estreia",
      "2023-07-05", "Márcio Anaya",
      "CPFE3 ingressou em 2 portfólios indicados para julho com 4 recomendações totais — primeira vez no ano entre os "
      "mais citados. BTG Pactual: 'CPFE3 negociada a TIR real de 10,2%, entregou fortes resultados operacionais que "
      "permitiram volumes expressivos de dividendos nos últimos 2 anos'. 'CPFL distribuiu payout de 100% nos últimos 2 "
      "anos, fundamental para excelente desempenho das ações em 2022'. Mercado seguirá decisões de alocação de capital."),

    C("https://www.infomoney.com.br/mercados/cpfl-cpfe3-tem-lucro-liquido-de-r-137-bilhao-no-quarto-trimestre-alta-de-33-no-ano/",
      "CPFE3", "CPFL (CPFE3) tem lucro líquido de R$ 1,37 bilhão no 4T22, alta de 3,3%",
      "2023-03-16", "Vitor Azevedo",
      "Lucro de R$1,3bi no 4T22 (+3,3% YoY). Receita recuou 2,9% YoY para R$10,3bi. Distribuição -2,6% para R$8,7bi. "
      "Industrial -0,2%, comercial -1%. Menores gastos com energia comprada (R$6,02bi para R$4,6bi). PMSO -37,5%, "
      "efeito positivo de remensuração da Enercan (+R$670mi). Ebitda +47,7% para R$3,5bi (Enercan). Dívida líquida "
      "R$23,4bi. Reportagem de balanço."),
]

TAEE11 = [
    C("https://www.infomoney.com.br/onde-investir/taesa-taee11-dividendos-moderados-2023-conheca-nova-eletrica-favorita-dos-analistas/",
      "TAEE11", "Dividendos da Taesa secaram? Elétrica muda estratégia",
      "2023-05-12", "Katherine Rivas",
      "Taesa não deixará de pagar dividendos, mas estará em fase de proventos não tão polpudos como os 14% de DY do "
      "ano passado. Dividendos mais conservadores, ainda superiores a 6%, parte do novo normal. Analistas projetam DY "
      "de 7%-11% para 2023, possibilidade de aumento gradual em 2024. De 16 instituições, 10 manter, 3 compra, 3 "
      "venda. XP: 'melhor pagadora de dividendos entre transmissoras', DY 11% 2023, recomendação manter, preço-alvo "
      "R$37 — 'sem espaço para valorização'. VG: manter, DY 8%, payout 80% — 'melhora gradual em 2024'. Suno: venda, "
      "DY 7-7,5%. Schweitzer: compra, DY 8% para 2023."),

    C("https://www.infomoney.com.br/mercados/taesa-taee11-busca-equilibrio-dividendos-crescimento-alavancagem-acoes-caem-balanco/",
      "TAEE11", "Taesa (TAEE11) busca equilíbrio entre dividendos, crescimento e alavancagem",
      "2023-03-16", "Augusto Diniz",
      "Taesa enfatiza importância de seguir plano estratégico de crescimento — leilões de transmissão e entrega de "
      "projetos arrematados. Empresa seguirá pagamento de dividendos previsto no estatuto. Tripé: proventos, "
      "investimentos e alavancagem. Morgan Stanley underweight, ação pouco atraente vs concorrentes apesar de "
      "dividendos acima dos pares; preço-alvo R$35. Itaú BBA: resultados 4T22 neutros. Ebitda 7% abaixo do esperado, "
      "alavancagem estável em 3,7x mas projetam aumento (>4x) por capex de projetos em construção. BBA underperform, "
      "preço-alvo R$35,95."),

    C("https://www.infomoney.com.br/mercados/alupar-alup11-isa-cteep-trpl4-e-taesa-taee11-pagam-bons-dividendos-mas-por-que-a-xp-nao-recomenda-compra-para-as-acoes/",
      "TAEE11", "Por que a XP não recomenda compra para as ações de transmissoras",
      "2023-09-07", "Felipe Moreira",
      "XP manteve neutra para Taesa, preço-alvo R$26 — vê TAEE11 negociando a TIR real alavancada de 6,2% vs 7,1% dos "
      "pares e diferença de 0,7% sobre NTN-B. Taesa empresa de alta qualidade, defensiva, baixo beta com fluxos de "
      "caixa previsíveis, mas 'essa chamada já se concretizou'. Margem Ebitda elevada, ativos mais jovens, carteira "
      "puramente de transmissão, controle de custos rígido. XP espera redução gradual da alavancagem com projetos "
      "operacionais, nível atual confortável para investimentos e dividendos."),

    C("https://www.infomoney.com.br/mercados/taesa-taee11-resultados-terceiro-trimestre-2023-anuncio-dividendos-jcp/",
      "TAEE11", "Taesa (TAEE11) tem lucro regulatório de R$ 330 milhões no 3T23 (-11,6%)",
      "2023-11-09", "Equipe InfoMoney",
      "Lucro regulatório de R$330,2mi no 3T23 (-11,6% YoY). Receita líquida IFRS R$686,5mi (+48,0%). Receita "
      "regulatória R$831,7mi (+6%) por início de Saíra, novas fases de Sant'Ana (94% RAP) e reajuste IPCA. Aprovou "
      "R$204,55mi em dividendos+JCP (R$0,59/Unit). Reportagem de balanço."),

    C("https://www.infomoney.com.br/onde-investir/dividendos-de-energia-taee11-trpl4-ou-alup11-veja-quanto-r-5-mil-rendem-nelas/",
      "TAEE11", "Dividendos de energia: TAEE11, TRPL4 ou ALUP11?",
      "2024-04-15", "Monique Lima",
      "Rossetti (Melver): 'Taesa foi destaque nos últimos anos, valorização +140% em 5 anos, DY médio 7,4%. Mas, "
      "olhando à frente, está em estágio mais maduro. Algumas concessões vencem primeiro, gestão não tão ativa em "
      "leilões recentes. Alavancagem 3,7x dívida líquida/Ebitda, maior das três'. Volume de pagamentos pode diminuir "
      "no futuro. AGF: estima DY de 9,6% para Taesa em 2024, R$3,54/ação. Destaca recorrência de 4 pagamentos no ano. "
      "'Empresa não competitiva em relação aos pares; ISA CTEEP tem conjunto mais promissor para futuro'."),
]

CMIG4 = [
    C("https://www.infomoney.com.br/mercados/cemig-cmig4-da-privatizacao-a-federalizacao-tese-para-acoes-tem-forte-virada-e-traz-duvidas-no-mercado-o-que-esperar/",
      "CMIG4", "Cemig (CMIG4): da privatização à federalização, tese sofre forte virada",
      "2023-11-23", "Lara Rizério",
      "Em poucos meses, tese de investimentos em Cemig sofreu reviravolta. Federalização seria negativa para empresas. "
      "Genial mantém manutenção dado cenário de volatilidade. BBI neutra, preço-alvo R$13. Após queda de 10%, ação "
      "negocia a TIR real de 11,9% — justa para estatal. Caso Cemig seja federalizada, TIR real subiria para 15-17%, "
      "implicando preço de R$8,90-R$7,50. Negociada a R$11,30, ainda teria espaço para baixa de 21-33%. BBA: 'difícil "
      "encontrar conforto em ponto de entrada bom em meio à queda, dadas implicações da mudança na equipe e "
      "estratégia. Ações poderiam recuperar caso federalização se mostre inviável'."),

    C("https://www.infomoney.com.br/mercados/jpmorgan-eleva-cemig-cmig4-e-camil-caml3-compra-rebaixa-alupar-alup11-e-mantem-marcopolo-pomo4-top-pick-acoes-reagem/",
      "CMIG4", "JPMorgan eleva Cemig (CMIG4) à compra",
      "2023-08-30", "Lara Rizério, Felipe Moreira",
      "JPMorgan elevou CMIG4 para compra, ações subiram 1,53% para R$12,61 (após +3% intraday). 'Utilities estatais "
      "controladas por Minas Gerais estão sendo mal avaliadas pelo mercado'. Cemig apresenta bons resultados, capex de "
      "crescimento com retornos atrativos e avaliação atraente. Concessionária integrada com forte projeção de lucros "
      "2023, conclusão da revisão tarifária em maio, ganhos no negócio de geração e transmissão. JPM vê Cemig com TIR "
      "implícita de 12,2% (vs média setor 11,6%), 5x EV/Ebitda 2024-2025. 'Segmento de distribuição não fica exposto a "
      "risco de renovação de concessão'. Preço-alvo R$16 ao fim de 2024, upside 29%, retorno total 42%."),

    C("https://www.infomoney.com.br/mercados/cemig-cmig4-cai-mais-de-10-com-noticia-de-que-governo-de-mg-aceitou-repassar-ativos-para-abater-divida-com-uniao/",
      "CMIG4", "Cemig (CMIG4) fecha em queda de quase 10% com notícia de federalização",
      "2023-11-22", "Equipe InfoMoney",
      "Ações da Cemig caíram 9,71% para R$11,35 após notícia de que governador de MG concordou em repassar ativos para "
      "abater dívida com União. Banco: 'Cemig e Copasa têm equipe de gestão muito boa, mas dado caminho desafiador da "
      "federalização, não entraríamos em pânico mas também não compraríamos com a fraqueza dos papéis pois poderá haver "
      "mais fluxo de notícias políticas'. BBA: 'difícil encontrar conforto em ponto de entrada bom em meio à queda, "
      "ações poderiam recuperar caso proposta de federalização se mostre inviável'."),

    C("https://www.infomoney.com.br/mercados/cemig-cmig4-se-prepara-internamente-para-privatizacao-e-divulga-plano-para-investir-r-422-bi-ate-2027/",
      "CMIG4", "Cemig se prepara para privatização e divulga plano de R$ 42,2 bi até 2027",
      "2023-03-27", "Equipe InfoMoney",
      "Cemig está em processo de turnaround que prepara para eventual privatização. Presidente do conselho vê ambiente "
      "mais favorável para aprovação legislativa, acredita que 'projeto sai neste mandato'. R$34bi gastos pela Cemig "
      "no passado em participações minoritárias 'destruíram valor'. Plano de investimentos R$42,2bi entre 2023-2027 — "
      "maior da história, vs R$22,5bi do plano anterior. Distribuição R$18,4bi (maior aporte), geração R$13,4bi, "
      "transmissão R$3,5bi. Foco em Minas Gerais."),
]


TICKERS = {
    "ITUB4": ITUB4, "BBDC4": BBDC4, "BBAS3": BBAS3, "SANB11": SANB11, "ABCB4": ABCB4,
    "EGIE3": EGIE3, "EQTL3": EQTL3, "CPFE3": CPFE3, "TAEE11": TAEE11, "CMIG4": CMIG4,
}


def main() -> None:
    summary = []
    for tkr, raw in TICKERS.items():
        deduped = dedupe(raw)
        kept, drops = filter_candidates(deduped)
        path = save_candidates(tkr, kept)
        summary.append({"ticker": tkr, "raw": len(raw), "deduped": len(deduped),
                        "kept": len(kept), "drops": drops, "path": str(path)})
    for s in summary:
        print(f"{s['ticker']}: raw={s['raw']} deduped={s['deduped']} kept={s['kept']} drops={s['drops']}")


if __name__ == "__main__":
    main()
