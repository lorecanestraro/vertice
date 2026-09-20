# Vértice Retail — painel de rentabilidade comercial

Painel em Streamlit para acompanhar margem, desconto, frete e devoluções da Vértice Retail,
varejista fictícia do case do AI Consulting Lab (Bootcamp EloGroup 2026). Todo número exibido é
calculado a partir da base tratada do data room, sobre o recorte de filtros ativo. Os insights não
são fixos: são gerados sob demanda pelo Elo Agents, a partir dos mesmos números.

## Requisitos

Python 3.12 e as versões fixadas em `requirements.txt` (Streamlit 1.63, pandas 3.0, Plotly 7.0,
openai 3.14). Para gerar a base, as planilhas do data room precisam estar na raiz do projeto.

## Como rodar

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python "tratamento_base_V@.py"   # gera os CSVs tratados; só quando o data room mudar
streamlit run app.py
```

O app lê apenas os CSVs tratados. Se eles já estiverem na pasta, o tratamento pode ser pulado.

## Dados

Entrada, não versionada (o data room entrega CSVs com extensão `.xlsx`, e o leitor trata isso):

| Arquivo | Conteúdo |
| --- | --- |
| `vendas.xlsx` | pedidos, obrigatório |
| `atendimento.xlsx` | chamados do SAC |
| `estoque.xlsx` | cadastro de SKUs |
| `clientes.xlsx` | cadastro de clientes |

Saída do tratamento:

| Arquivo | Conteúdo |
| --- | --- |
| `vendas_tratada.csv` | 24.454 pedidos aprovados, de 01/01/2023 a 26/01/2024, com 42 colunas derivadas |
| `atendimento_tratado.csv` | 35.841 chamados, encoding corrigido e datas normalizadas |
| `estoque_tratado.csv` | 5.000 SKUs |
| `calendario_sazonal.csv` | índice mensal de volume, receita e itens (base 2023) |
| `clientes_tratado.csv` | cadastro sem dados pessoais; não é usado pelo app e não deve ser versionado |

O tratamento imprime as checagens de identidade contábil (margem = receita líquida − CMV − frete,
receita líquida = bruta − desconto, receita bruta = quantidade × preço) e a aderência da regra de
frete. Qualquer divergência aparece como `FALHOU` no console.

## Definições

O universo do painel são os pedidos aprovados. Pedidos cancelados e "Aguardando" ficam fora da base
tratada, e por isso não aparecem como perda.

- **Margem de contribuição**: receita líquida − CMV − frete, sobre a receita líquida.
- **Margem realizada**: o pedido devolvido é reembolsado, perdendo a receita e o frete de ida; o item
  volta ao estoque, então o CMV não conta como perda. É a definição do business case.
- **Margem realizada com atendimento**: desconta também os chamados ligados àqueles pedidos e abertos
  depois do pedido.

A aba Visão geral traz um bloco com o universo e a fórmula de cada indicador, e por que os totais
diferem dos da apresentação ao comitê.

## Conciliação com o business case

O case cobre 2023 fechado; o painel abre no período completo. Selecionando "Ano de 2023" no filtro,
os indicadores reproduzem a apresentação:

| Indicador | Painel | Deck |
| --- | --- | --- |
| Margem de contribuição | 54,34% | 54,34% |
| Margem realizada com atendimento | 53,08% | 53,08% |
| Descontos concedidos | R$ 1.389.865 | R$ 1.389.865 |
| Frete pago | R$ 284.237 | R$ 284.237 |
| Margem perdida em devoluções | R$ 1.335.908 | R$ 1,34 mi |
| Teto de 20% fora de novembro | R$ 241,4 mil | R$ 241,4 mil |

O simulador abre no cenário atual, com as alavancas em zero. O botão "Aplicar o cenário do business
case" posiciona as alavancas na proposta levada ao comitê.

## Abas

| Aba | O que responde |
| --- | --- |
| Visão geral | evolução do período, margem por canal, composição da margem e a conclusão do recorte |
| Explorar | self-service: dimensão, métrica e quebra livres, com clique no gráfico para listar pedidos |
| Canais | custos por canal, receita e margem por canal e categoria, margem mensal |
| Desconto | margem e itens por faixa de desconto, sazonalidade, desconto acima de 25% por canal |
| Frete e entrega | aderência da regra de frete, prazo por canal, frete por faixa de ticket |
| Devoluções | motivos, relação com prazo de entrega e mapa de canal por categoria |
| Atendimento | custo, satisfação, volume mensal e tempo de resposta do SAC |
| Alertas | lista para ação diária, com o tamanho do problema e o valor recuperável separados |
| Simulador | efeito de teto de desconto, frete do Marketplace e redução de devoluções |

## Insights sob demanda

A geração usa o gateway Elo Agents, compatível com a API da OpenAI. A chave fica em
`.streamlit/secrets.toml`, que está no `.gitignore` (veja `.streamlit/secrets.toml.example`):

```toml
ELOAGENTS_API_KEY = "sua-chave"
```

Para diagnosticar a conexão: `python elo_agents.py`.

O painel envia apenas indicadores agregados do recorte, sem identificação de cliente ou pedido, e
confere cada número citado na resposta contra os dados enviados. Números que não batem recebem um
selo de alerta. A conferência cobre os números, não a interpretação: o texto continua exigindo
leitura crítica. Sem chave configurada, o painel funciona normalmente, apenas sem os insights.

## Tema

O painel segue o Vértice Retail Design System: indigo sobre off-white, com navy como única
superfície escura. O botão no cabeçalho alterna para o tema escuro, que recarrega a página com
`?tema=escuro` na URL, porque os componentes nativos do Streamlit só trocam de tema ao carregar.

## Deploy

No Streamlit Community Cloud, aponte o app para `app.py` e cadastre `ELOAGENTS_API_KEY` em
Settings > Secrets. Os CSVs tratados precisam estar versionados, já que o data room não vai para o
repositório. `clientes.xlsx` e `clientes_tratado.csv` contêm dados pessoais e não devem subir.

## Estrutura

```
app.py                    painel: paleta, gráficos, filtros e abas
elo_agents.py             integração com o gateway, prompts e conferência de números
tratamento_base_V@.py     leitura do data room, limpeza, colunas derivadas e checagens
.streamlit/config.toml    tema dos componentes nativos (claro e escuro)
```

## Limitações conhecidas

A base do case é sintética, e algumas relações não se sustentam. Elas estão declaradas aqui porque
limitam o que o painel pode afirmar:

- 331 clientes para 24 mil pedidos, com um único cliente respondendo por 40,7% deles. Não há
  segmentação de clientes no painel.
- Os chamados do SAC não se ligam aos pedidos de forma confiável: só cerca de um terço dos
  `order_id` existe na base de vendas, e parte dos chamados abre antes do pedido. A aba Atendimento
  analisa os chamados por data, canal de entrada e motivo, sem cruzar com vendas.
- No cadastro de estoque, custo unitário e preço sugerido não reconciliam com os valores praticados
  nos pedidos. Só o cadastro (subcategoria, fornecedor, situação) é usado.
- A situação do estoque é a posição na data de extração, não na data do pedido.
- Há um único ano completo (2023), então a leitura sazonal vem de um ciclo só.
- Não há investimento de mídia, comissão de marketplace nem custo logístico reverso na base: a
  rentabilidade por canal é parcial.
