# insightBrasil
Agregado de dados de diversas fontes para encontrar insights e aprender

Origem dos dados

**[Operações COPEM (SADIPEM)](https://dados.gov.br/dados/conjuntos-dados/operacoes-copem)**
Pedidos de estados e municípios à União para realizar operações de crédito (empréstimos, financiamentos, garantias), analisados e registrados pelo Tesouro Nacional através do sistema SADIPEM. Cada registro traz o ente interessado, o credor, a finalidade do crédito, o valor solicitado, o status da análise (deferido, indeferido, arquivado etc.) e a data de tramitação.

**[Transferências Constitucionais para Municípios](https://dados.gov.br/dados/conjuntos-dados/transferencias-constitucionais-para-municipios)**
Repasses mensais que a União faz aos municípios por determinação constitucional — FPM, FPE, FUNDEB, ICMS, IPVA, ITR, CIDE-Combustíveis, entre outros. Os valores são detalhados por município, UF, ano, mês e decêndio (períodos de dez dias em que o repasse é dividido).

Coleta dos dados

**`scripts/download_data.py`**
Baixa os CSVs dos dois conjuntos direto da API CKAN do Tesouro Transparente, mantendo apenas uma janela rolante dos últimos 12 anos — o suficiente para comparar três mandatos presidenciais. A cada execução, baixa o que for novo e remove localmente o que saiu da janela, então `data/` nunca cresce sem limite.

**`scripts/download_population.py`**
Baixa do IBGE a estimativa populacional de cada UF e salva em `data/populacao_uf.csv`, usada pela análise per capita abaixo.

Análises (`scripts/`)

**`correlate.py`**
Correlação entre o valor/quantidade de operações de crédito aprovadas no SADIPEM e o total de transferências recebidas, por UF e ano. Calcula tanto Pearson quanto Spearman (por postos): o pool de 11 anos de dados mistura escalas bem diferentes e é dominado por operações extraordinárias de um único estado num único ano (ex.: a renegociação de ~R$ 224 bilhões de SP em 2017), o que distorce Pearson — Spearman, por trabalhar com postos em vez de valores brutos, é bem mais resistente a esse tipo de outlier.

**`per_capita.py`**
Reclassifica os estados por transferências recebidas e crédito aprovado *por habitante* (usando as estimativas do IBGE), em vez de valores brutos — onde São Paulo deixa de liderar todo ranking só por ser o estado mais populoso, e estados menores como TO, AL e PI aparecem no topo ao normalizar pelo tamanho da população.

**`debt_to_revenue.py`**
Razão entre o crédito aprovado pelo SADIPEM e as transferências recebidas, por estado e ano — uma medida mais direta de "quanto este estado está se endividando em relação à sua receita constitucional" do que um coeficiente de correlação consegue dar.

**`trends.py`**
Evolução ano a ano dos totais nacionais de cada conjunto, com variação percentual — a trajetória ao longo do tempo, sem resumir tudo num único número, com o ano corrente sinalizado como "em andamento" para não distorcer a comparação.

**`purposes_and_creditors.py`**
Para que servem as operações de crédito aprovadas (campo Finalidade) e quem empresta (campos Credor / Tipo de credor) — transforma "quais estados pegam mais crédito" em "pegam para quê, e de quem". Mais da metade do valor aprovado no período é renegociação de dívida, concentrada em pouquíssimas operações.

**`approval_rates.py`**
Taxa de aprovação dos pedidos de crédito no SADIPEM (Deferido vs. Indeferido vs. Arquivado) — no geral, por ano e por estado, revelando o quanto o processo é seletivo e como isso varia.

**`pandemic_spotlight.py`**
Compara 2020-2021 (pandemia de COVID-19) com os anos imediatamente antes e depois, destacando o quão fora da curva esse período foi: o valor de crédito aprovado disparou (+118% sobre a média da linha de base) bem na hora em que as transferências recebidas caíram — exatamente o tipo de evento extraordinário que uma análise "ano a ano normal" tende a esconder dentro de uma média.
