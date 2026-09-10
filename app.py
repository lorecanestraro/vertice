"""
Vértice Retail — Cockpit de Rentabilidade
Bootcamp EloGroup 2026 | AI Consulting Lab

Como rodar:
    pip install streamlit plotly pandas numpy
    streamlit run app.py

Requer 'vendas_tratada.csv' e 'calendario_sazonal.csv' no mesmo diretório
(gerados por tratamento_base_V@.py).
"""

from string import Template

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ======================================================================
# IDENTIDADE VISUAL — Manual Vértice Retail
# ======================================================================
ELO_BLUE = "#1E1EE0"
MAGENTA = "#D6249A"
ROXO = "#6E2BD9"
CIANO = "#0EA5E9"
AMBAR = "#F59E0B"
SUCESSO = "#16A34A"
ERRO = "#DC2626"
GRAFITE = "#171717"
CINZA_ESCURO = "#3F3F46"
CINZA_MEDIO = "#71717A"
CINZA_CLARO = "#E4E4E7"
BRANCO_GELO = "#FAFAFA"

PALETA = [ELO_BLUE, MAGENTA, ROXO, CIANO, AMBAR, SUCESSO, CINZA_MEDIO, ERRO]
COR_CANAL = {
    "Marketplace": MAGENTA,
    "Google Ads": ELO_BLUE,
    "Instagram Ads": ROXO,
    "Orgânico": SUCESSO,
    "TikTok Ads": CIANO,
    "Email Marketing": AMBAR,
    "Influenciador": CINZA_MEDIO,
}
COR_CATEGORIA = {"Moda": ELO_BLUE, "Beleza": MAGENTA, "Lifestyle": ROXO, "Acessórios": CIANO}

st.set_page_config(page_title="Vértice Retail — Cockpit de Rentabilidade",
                   page_icon="◆", layout="wide", initial_sidebar_state="expanded")

# ======================================================================
# TEMA
# ----------------------------------------------------------------------
# O cockpit NÃO herda o tema do Streamlit: toda superfície e todo texto
# são pinados na paleta do manual, para que a leitura seja idêntica com o
# usuário em tema claro ou escuro. Renderizado com st.html — que não passa
# pelo parser de markdown; via st.markdown o bloco era cortado na primeira
# linha em branco e o CSS vazava como texto no topo da página.
# ======================================================================
CSS = Template("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
:root { color-scheme: light; }
html, body, .stApp,
[data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMainBlockContainer"] { background: $BRANCO_GELO !important; color: $GRAFITE !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] svg { fill: $CINZA_MEDIO !important; }
.block-container { padding-top: 2.2rem; max-width: 1500px; }
html, body, [class*="css"], [data-testid="stMarkdownContainer"] {
   font-family: 'Inter', Helvetica, Arial, sans-serif; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { color: $CINZA_ESCURO; }
h1, h2, h3, h4 { font-family: 'Space Grotesk', Montserrat, Arial, sans-serif !important;
   color: $GRAFITE !important; }
h1 { font-size: 34px !important; font-weight: 700 !important; letter-spacing: -0.02em; }
h2 { font-size: 23px !important; font-weight: 600 !important; margin-top: 8px !important;
     letter-spacing: -0.01em; }
h3 { font-size: 18px !important; font-weight: 600 !important; }
hr { margin: 10px 0 22px; border-color: $CINZA_CLARO; }
.hero { background: linear-gradient(115deg, $GRAFITE 0%, #241947 55%, $ROXO 130%);
        border-radius: 18px; padding: 30px 34px; margin-bottom: 8px; }
.hero h1 { color: #FFFFFF !important; margin: 0; }
.hero p { color: rgba(255,255,255,.75) !important; font-size: 15px; margin: 8px 0 0 0; }
.hero .tag { display:inline-block; background: rgba(255,255,255,.12);
   border:1px solid rgba(255,255,255,.20); border-radius:999px; padding:4px 12px;
   font-size:12px; font-weight:600; margin-right:8px; color:#FFFFFF; }
.kpi { background:#FFFFFF; border:1px solid $CINZA_CLARO; border-radius:14px;
   padding:22px 22px 20px; height:100%; position:relative; overflow:hidden;
   box-shadow: 0 1px 2px rgba(23,23,23,.04); }
.kpi::before { content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background:$ELO_BLUE; }
.kpi.danger::before { background:$ERRO; }
.kpi.ok::before { background:$SUCESSO; }
.kpi.warn::before { background:$AMBAR; }
.kpi-label { font-size:12.5px; color:$CINZA_MEDIO; font-weight:600; margin-bottom:6px;
   text-transform:uppercase; letter-spacing:.04em; }
.kpi-value { font-family:'Space Grotesk',sans-serif; font-size:38px; font-weight:700;
   line-height:1.05; color:$GRAFITE; }
.kpi-sub { font-size:12.5px; margin-top:8px; font-weight:500; color:$CINZA_MEDIO; }
.kpi-sub b { font-weight:700; color:$CINZA_ESCURO; }
.msg { font-size:15.5px; color:$CINZA_ESCURO !important; margin:4px 0 18px 0; line-height:1.5;
   border-left:4px solid $MAGENTA; padding-left:16px; }
.nota { font-size:12.5px; color:$CINZA_MEDIO !important; margin-top:8px; line-height:1.45; }
.stTabs [data-baseweb="tab-list"] { gap:30px; background:transparent !important;
   border-bottom:1px solid $CINZA_CLARO; }
.stTabs [data-baseweb="tab"] { background:transparent !important; color:$CINZA_MEDIO !important;
   padding-top:8px; padding-bottom:12px; }
.stTabs [data-baseweb="tab"] p { color:inherit !important; font-family:'Inter';
   font-weight:600 !important; font-size:15px !important; }
.stTabs [data-baseweb="tab"]:hover { color:$GRAFITE !important; }
.stTabs [aria-selected="true"], .stTabs [aria-selected="true"] p { color:$ELO_BLUE !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color:$ELO_BLUE !important; }
.stTabs [data-baseweb="tab-border"] { background-color:$CINZA_CLARO !important; }
[data-testid="stSidebar"], [data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] { background:#FFFFFF !important; }
[data-testid="stSidebar"] { border-right:1px solid $CINZA_CLARO; }
[data-testid="stSidebar"] h2 { font-size:16px !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color:$CINZA_ESCURO !important; }
[data-testid="stWidgetLabel"] p { color:$CINZA_ESCURO !important; font-weight:600 !important;
   font-size:13px !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:$CINZA_MEDIO !important; }
[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="base-input"] {
   background-color:#FFFFFF !important; border-color:$CINZA_CLARO !important; color:$GRAFITE !important; }
[data-baseweb="select"] svg { fill:$CINZA_MEDIO !important; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"], [data-baseweb="menu"] li {
   background-color:#FFFFFF !important; color:$GRAFITE !important; }
[data-baseweb="menu"] li:hover { background-color:$BRANCO_GELO !important; }
[data-baseweb="tag"] { background-color:$ELO_BLUE !important; border-color:$ELO_BLUE !important; }
[data-baseweb="tag"] span, [data-baseweb="tag"] svg { color:#FFFFFF !important; fill:#FFFFFF !important; }
[data-testid="stSlider"] [role="slider"] { background-color:$ELO_BLUE !important; }
[data-testid="stThumbValue"] { color:$ELO_BLUE !important; font-weight:600 !important; }
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] {
   color:$CINZA_MEDIO !important; background:transparent !important; }
[data-testid="stCheckbox"] p { color:$CINZA_ESCURO !important; }
/* O Streamlit fixa a altura deste container; border e padding roubariam essa
   altura por dentro e cortariam o título do eixo x. A moldura vem de box-shadow,
   que é puramente visual e não consome layout. */
[data-testid="stPlotlyChart"] { background:#FFFFFF; border:none; padding:0;
   border-radius:14px; box-shadow: 0 0 0 1px $CINZA_CLARO, 0 1px 2px rgba(23,23,23,.05); }
.modebar { background:transparent !important; }
</style>
""").substitute(
    ELO_BLUE=ELO_BLUE, MAGENTA=MAGENTA, ROXO=ROXO, AMBAR=AMBAR, SUCESSO=SUCESSO, ERRO=ERRO,
    GRAFITE=GRAFITE, CINZA_ESCURO=CINZA_ESCURO, CINZA_MEDIO=CINZA_MEDIO,
    CINZA_CLARO=CINZA_CLARO, BRANCO_GELO=BRANCO_GELO,
)
st.html(CSS)


# ======================================================================
# HELPERS
# ======================================================================
def layout(fig, altura=400, titulo=None):
    """Padrão visual do manual. As margens são mínimas de propósito: quem reserva
    o espaço real dos rótulos e títulos de eixo é o automargin — sem ele, nomes de
    canal e valores em R$ ficam cortados na borda esquerda."""
    # o título pode vir no argumento OU já ter sido definido na figura; nunca
    # sobrescrever com None, senão os títulos definidos antes de layout() somem
    titulo = titulo or (fig.layout.title.text if fig.layout.title else None)
    fig.update_layout(
        height=altura, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        title=dict(text=titulo, font=dict(family="Space Grotesk", size=16, color=GRAFITE),
                   x=0, xanchor="left") if titulo else None,
        font=dict(family="Inter, Helvetica, Arial", size=12.5, color=CINZA_ESCURO),
        margin=dict(l=12, r=30, t=52 if titulo else 24, b=24),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=GRAFITE, font=dict(color="#FFFFFF", family="Inter", size=12.5)),
        bargap=0.28,
        separators=",.",  # 1.234,56 — padrão pt-BR nos eixos e tooltips
    )
    fig.update_xaxes(showgrid=False, linecolor=CINZA_CLARO, ticks="outside",
                     tickcolor=CINZA_CLARO, tickfont=dict(size=12), automargin=True,
                     title_font=dict(size=12.5, color=CINZA_MEDIO))
    fig.update_yaxes(gridcolor="#F0F0F2", zerolinecolor=CINZA_CLARO, tickfont=dict(size=12),
                     automargin=True, title_font=dict(size=12.5, color=CINZA_MEDIO))
    # rótulos textposition="outside" extrapolam o eixo; sem isto são cortados
    fig.update_traces(cliponaxis=False, selector=dict(type="bar"))
    return fig


def brl(v, casas=0):
    s = f"R$ {v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def milhoes(v):
    return f"R$ {v/1e6:,.2f} mi".replace(".", ",")


def num(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def inteiro(v):
    return f"{v:,.0f}".replace(",", ".")


def kpi(col, label, valor, sub, tom=""):
    col.markdown(f"""<div class="kpi {tom}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{valor}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)


def mpct(g):
    """Margem de contribuição % sobre receita líquida de um recorte."""
    r = g["receita_liquida"].sum()
    return np.nan if r == 0 else g["margem_contribuicao"].sum() / r * 100


# ======================================================================
# DADOS
# ======================================================================
# O CSV perde o tipo Categorical das faixas: elas voltam como texto e o groupby
# passa a ordenar em ordem alfabética ("<100" cairia entre "500-1000" e ">1000").
# A ordem é a mesma definida nos pd.cut de tratamento_base_V@.py.
ORDEM_TICKET = ["<100", "100-200", "200-250", "250-300", "300-500", "500-1000", ">1000"]
ORDEM_DESCONTO = ["0%", "0-10%", "10-20%", "20-25%", "25-30%", ">30%"]


@st.cache_data
def carregar():
    df = pd.read_csv("vendas_tratada.csv", parse_dates=["data_pedido"])
    cal = pd.read_csv("calendario_sazonal.csv", index_col=0)
    df["mes_nome"] = df["data_pedido"].dt.strftime("%b/%y")
    df["faixa_ticket"] = pd.Categorical(df["faixa_ticket"], ORDEM_TICKET, ordered=True)
    df["faixa_desconto"] = pd.Categorical(df["faixa_desconto"], ORDEM_DESCONTO, ordered=True)
    return df, cal


BASE, cal = carregar()

# ======================================================================
# SIDEBAR — FILTROS
# ======================================================================
with st.sidebar:
    st.markdown("## ◆ Filtros")
    st.caption("Recortam todos os indicadores e gráficos do cockpit.")

    canais_sel = st.multiselect("Canal", sorted(BASE["canal"].unique()),
                                default=sorted(BASE["canal"].unique()))
    cats_sel = st.multiselect("Categoria", sorted(BASE["categoria"].unique()),
                              default=sorted(BASE["categoria"].unique()))
    pgto_sel = st.multiselect("Método de pagamento", sorted(BASE["metodo_pagamento"].unique()),
                              default=sorted(BASE["metodo_pagamento"].unique()))
    incluir_dev = st.checkbox("Incluir pedidos devolvidos", value=True)

    st.markdown("---")
    st.caption("Base: pedidos aprovados · jan/2023 a jan/2024 · "
               "margem de contribuição = receita líquida − CMV − frete.")

df = BASE[
    BASE["canal"].isin(canais_sel or BASE["canal"].unique())
    & BASE["categoria"].isin(cats_sel or BASE["categoria"].unique())
    & BASE["metodo_pagamento"].isin(pgto_sel or BASE["metodo_pagamento"].unique())
].copy()
if not incluir_dev:
    df = df[~df["devolvido"]]

if df.empty:
    st.warning("Nenhum pedido no recorte selecionado. Ajuste os filtros na barra lateral.")
    st.stop()

# ======================================================================
# INDICADORES
# ======================================================================
R = df["receita_liquida"].sum()
RB = df["receita_bruta"].sum()
M = df["margem_contribuicao"].sum()
CMV = df["custo_produto"].sum()
DESC = df["desconto_reais"].sum()
FRETE = df["custo_frete"].sum()
DESC25 = df.loc[df["desconto_acima_25"], "desconto_reais"].sum()
FRETE_MK = df.loc[df["mk_elegivel_nao_subsidiado"], "custo_frete"].sum()
CONCESSOES = DESC + FRETE
N = len(df)
N_NEG = int(df["margem_negativa"].sum())
TX_DEV = df["devolvido"].mean() * 100
PERDA_DEV = df.loc[df["devolvido"], ["custo_produto", "custo_frete"]].sum().sum()
M_REAL = df["margem_realizada"].sum()
R_REAL = df["receita_realizada"].sum()
MARGEM_REAL_PCT = M_REAL / R_REAL * 100 if R_REAL else np.nan
# Cenário-base: 100% do frete MK não subsidiado + recuperação de 20% do desconto
# acima de 25% (premissa conservadora — ajustável na aba Simulador).
RECUP_DESC_BASE = 0.20
OPORTUNIDADE = FRETE_MK + DESC25 * RECUP_DESC_BASE

# ======================================================================
# HERO
# ======================================================================
st.markdown(f"""
<div class="hero">
  <span class="tag">AI CONSULTING LAB</span><span class="tag">BOOTCAMP ELOGROUP 2026</span>
  <h1>Vértice Retail — onde a margem se perde</h1>
  <p>{inteiro(N)} pedidos aprovados &nbsp;·&nbsp; {milhoes(R)} de receita líquida &nbsp;·&nbsp;
     {df['customer_id'].nunique()} clientes &nbsp;·&nbsp; jan/2023 a jan/2024</p>
</div>
""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4, gap="medium")
kpi(k1, "Margem de contribuição", f"{num(M/R*100)}%",
    f"<b>{brl(M)}</b> sobre {brl(R)}", "ok" if M/R*100 >= 50 else "warn")
kpi(k2, "Margem realizada (líq. devolução)", f"{num(MARGEM_REAL_PCT)}%",
    f"−{num(M/R*100 - MARGEM_REAL_PCT)} p.p. vs. contábil · devoluções custam <b>{brl(PERDA_DEV)}</b>",
    "danger")
kpi(k3, "Concessões ao cliente", brl(CONCESSOES),
    f"<b>{num(CONCESSOES/RB*100)}%</b> da receita bruta — desconto ({brl(DESC)}) + frete ({brl(FRETE)})",
    "danger")
kpi(k4, "Oportunidade priorizada", brl(OPORTUNIDADE),
    f"+<b>{num(OPORTUNIDADE/R*100)} p.p.</b> de margem — frete MK + 20% do desconto &gt;25% "
    f"(premissa; ajuste na aba Simulador)", "ok")

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

t1, t2, t3, t4, t5, t6 = st.tabs([
    "Visão executiva", "Canais & Categorias", "Desconto", "Frete",
    "Devoluções & Entrega", "Simulador"])

# ======================================================================
# ABA 1 — VISÃO EXECUTIVA
# ======================================================================
with t1:
    cA, cB = st.columns([5, 4], gap="large")

    with cA:
        st.markdown("## Ponte da margem — do bruto ao contábil")
        st.markdown('<p class="msg">Cada real de receita bruta chega à margem depois de três '
                    'deduções. Desconto e frete são decisões comerciais — e é onde a Vértice '
                    'tem alavanca.</p>', unsafe_allow_html=True)
        w = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=["Receita bruta", "− Desconto", "− CMV", "− Frete", "Margem de contribuição"],
            y=[RB, -DESC, -CMV, -FRETE, M],
            text=[brl(RB), brl(-DESC), brl(-CMV), brl(-FRETE), brl(M)],
            textposition="outside", textfont=dict(size=12, color=GRAFITE),
            connector=dict(line=dict(color=CINZA_CLARO)),
            increasing=dict(marker=dict(color=SUCESSO)),
            decreasing=dict(marker=dict(color=MAGENTA)),
            totals=dict(marker=dict(color=ELO_BLUE)),
            hovertemplate="%{x}: %{text}<extra></extra>"))
        w.update_layout(showlegend=False,
                        yaxis=dict(tickprefix="R$ ", tickformat="~s", title=None))
        st.plotly_chart(layout(w, 420), theme=None, width="stretch")
        st.markdown(f'<p class="nota">Desconto e frete somam <b>{brl(CONCESSOES)}</b> — '
                    f'{num(CONCESSOES/RB*100)}% da receita bruta. O CMV '
                    f'({num(CMV/R*100)}% da receita líquida) é estável e fora de governança '
                    f'comercial de curto prazo.</p>', unsafe_allow_html=True)

    with cB:
        st.markdown("## Margem realizada ao longo do ano")
        st.markdown('<p class="msg">A margem contábil é plana. A realizada respira com as '
                    'devoluções e mergulha em novembro.</p>', unsafe_allow_html=True)
        mm = (df.groupby("ano_mes")
              .apply(lambda g: pd.Series({
                  "contabil": mpct(g),
                  "realizada": g["margem_realizada"].sum() / g["receita_realizada"].sum() * 100
                  if g["receita_realizada"].sum() else np.nan,
                  "receita": g["receita_liquida"].sum(),
              }), include_groups=False).reset_index())
        mm["rot"] = pd.to_datetime(mm["ano_mes"] + "-01").dt.strftime("%b/%y")
        ft = go.Figure()
        ft.add_bar(x=mm["rot"], y=mm["receita"], name="Receita líquida", yaxis="y2",
                   marker_color=CINZA_CLARO, hovertemplate="Receita: %{y:,.0f}<extra></extra>")
        ft.add_scatter(x=mm["rot"], y=mm["contabil"], name="Margem contábil (%)",
                       mode="lines+markers", line=dict(color=ELO_BLUE, width=3, dash="dot"),
                       marker=dict(size=7), hovertemplate="Contábil: %{y:.2f}%<extra></extra>")
        ft.add_scatter(x=mm["rot"], y=mm["realizada"], name="Margem realizada (%)",
                       mode="lines+markers", line=dict(color=MAGENTA, width=3),
                       marker=dict(size=8), hovertemplate="Realizada: %{y:.2f}%<extra></extra>")
        ft.update_layout(
            yaxis=dict(title="Margem (%)", range=[30, 62]),
            yaxis2=dict(title=None, overlaying="y", side="right",
                        showgrid=False, tickprefix="R$ ", tickformat="~s"))
        st.plotly_chart(layout(ft, 420), theme=None, width="stretch")
        st.markdown('<p class="nota">A distância entre as duas linhas é o custo das devoluções: '
                    f'<b>{brl(PERDA_DEV)}</b> em CMV e frete que não voltam.</p>',
                    unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## A diferença de margem entre canais é explicada pelo frete")
    st.markdown('<p class="msg">Custo do produto e desconto são equivalentes em todos os canais. '
                'Apenas o frete varia — e concentra-se no Marketplace.</p>',
                unsafe_allow_html=True)

    comp = (df.groupby("canal")
            .apply(lambda g: pd.Series({
                "CMV": g["custo_produto"].sum() / g["receita_liquida"].sum() * 100,
                "Frete": g["custo_frete"].sum() / g["receita_liquida"].sum() * 100,
                "Desconto": g["desconto_reais"].sum() / g["receita_bruta"].sum() * 100,
                "Margem": mpct(g),
            }), include_groups=False)
            .sort_values("Margem"))

    cc1, cc2 = st.columns([3, 2], gap="large")
    with cc1:
        fig = go.Figure()
        fig.add_bar(y=comp.index, x=comp["CMV"], name="Custo do produto", orientation="h",
                    marker_color=CINZA_MEDIO, hovertemplate="CMV: %{x:.2f}%<extra></extra>")
        fig.add_bar(y=comp.index, x=comp["Frete"], name="Frete (Marketplace em magenta)",
                    orientation="h",
                    marker_color=[MAGENTA if c == "Marketplace" else CIANO for c in comp.index],
                    text=[f"{v:.2f}%" for v in comp["Frete"]], textposition="outside",
                    textfont=dict(size=11, color=GRAFITE),
                    hovertemplate="Frete: %{x:.2f}%<extra></extra>")
        fig.add_bar(y=comp.index, x=comp["Desconto"], name="Desconto", orientation="h",
                    marker_color=ROXO, hovertemplate="Desconto: %{x:.2f}%<extra></extra>")
        fig.update_layout(barmode="stack", xaxis_title="% da receita líquida")
        st.plotly_chart(layout(fig, 420), theme=None, width="stretch")
    with cc2:
        mg = comp["Margem"].sort_values()
        f2 = go.Figure(go.Bar(
            y=mg.index, x=mg.values, orientation="h",
            marker_color=[MAGENTA if c == "Marketplace" else ELO_BLUE for c in mg.index],
            text=[f"{v:.2f}%" for v in mg.values], textposition="outside",
            textfont=dict(size=11), hovertemplate="%{y}: %{x:.2f}%<extra></extra>"))
        f2.update_layout(xaxis_title="Margem de contribuição (%)", xaxis_range=[0, 70],
                         showlegend=False, title=dict(text="Margem realizada por canal"))
        st.plotly_chart(layout(f2, 420), theme=None, width="stretch")
    outros = comp.drop("Marketplace", errors="ignore")["Margem"].mean()
    if "Marketplace" in comp.index:
        st.markdown(f'<p class="nota">O Marketplace opera <b>{num(outros - comp.loc["Marketplace","Margem"])} '
                    f'pontos</b> abaixo da média dos demais canais — diferença quase toda no frete.</p>',
                    unsafe_allow_html=True)

# ======================================================================
# ABA 2 — CANAIS & CATEGORIAS
# ======================================================================
with t2:
    st.markdown("## Mapa de rentabilidade dos canais")
    st.markdown('<p class="msg">Tamanho da bolha = receita líquida. Quanto mais à direita e '
                'mais abaixo, melhor: alta margem e baixo peso de frete.</p>',
                unsafe_allow_html=True)

    ch = (df.groupby("canal")
          .apply(lambda g: pd.Series({
              "margem": mpct(g),
              "frete_pct": g["custo_frete"].sum() / g["receita_liquida"].sum() * 100,
              "receita": g["receita_liquida"].sum(),
              "pedidos": len(g),
              "desconto_pct": g["desconto_reais"].sum() / g["receita_bruta"].sum() * 100,
              "dev": g["devolvido"].mean() * 100,
          }), include_groups=False).reset_index())

    bub = go.Figure()
    for _, row in ch.iterrows():
        bub.add_scatter(
            # legenda em vez de rótulo no ponto: seis dos sete canais ficam a
            # menos de 1,5 p.p. um do outro e os textos se sobrepunham
            x=[row["margem"]], y=[row["frete_pct"]], mode="markers", name=row["canal"],
            marker=dict(size=row["receita"] / ch["receita"].max() * 48 + 14,
                        color=COR_CANAL.get(row["canal"], ELO_BLUE),
                        line=dict(color="#FFFFFF", width=2), opacity=0.85),
            hovertemplate=(f"<b>{row['canal']}</b><br>Margem: {row['margem']:.2f}%<br>"
                           f"Frete: {row['frete_pct']:.2f}%<br>Receita: {brl(row['receita'])}<br>"
                           f"Pedidos: {inteiro(row['pedidos'])}<br>Devolução: {row['dev']:.1f}%<extra></extra>"),
            cliponaxis=False, showlegend=True)
    px_, py_ = (ch["margem"].max() - ch["margem"].min()) * 0.12 + 0.25, ch["frete_pct"].max() * 0.18 + 0.25
    bub.update_layout(xaxis_title="Margem de contribuição (%)",
                      yaxis_title="Frete (% da receita líquida)",
                      xaxis=dict(range=[ch["margem"].min() - px_, ch["margem"].max() + px_]),
                      yaxis=dict(range=[ch["frete_pct"].max() + py_, -py_ * 0.6]))
    st.plotly_chart(layout(bub, 440), theme=None, width="stretch")

    st.markdown("---")
    g1, g2 = st.columns(2, gap="large")
    with g1:
        st.markdown("### Receita e margem por categoria")
        catg = (df.groupby("categoria")
                .apply(lambda g: pd.Series({
                    "receita": g["receita_liquida"].sum(), "margem": mpct(g),
                }), include_groups=False).sort_values("receita", ascending=True))
        fc = go.Figure()
        fc.add_bar(y=catg.index, x=catg["receita"], orientation="h",
                   marker_color=[COR_CATEGORIA.get(c, ELO_BLUE) for c in catg.index],
                   text=[f"{milhoes(v)} · {m:.1f}%" for v, m in zip(catg["receita"], catg["margem"])],
                   textposition="outside", textfont=dict(size=11),
                   hovertemplate="%{y}: %{x:,.0f}<extra></extra>")
        fc.update_layout(xaxis_title="Receita líquida", showlegend=False,
                         xaxis=dict(tickprefix="R$ ", tickformat="~s"),
                         xaxis_range=[0, catg["receita"].max() * 1.25])
        st.plotly_chart(layout(fc, 320), theme=None, width="stretch")

    with g2:
        st.markdown("### Margem por canal × categoria")
        piv = df.pivot_table(index="canal", columns="categoria",
                             values="margem_contribuicao", aggfunc="sum")
        pivr = df.pivot_table(index="canal", columns="categoria",
                              values="receita_liquida", aggfunc="sum")
        mat = (piv / pivr * 100).round(1)
        hm = go.Figure(go.Heatmap(
            z=mat.values, x=mat.columns, y=mat.index,
            colorscale=[[0, ERRO], [0.5, AMBAR], [1, ELO_BLUE]],
            text=mat.values, texttemplate="%{text}%", textfont=dict(size=11),
            hovertemplate="%{y} · %{x}: %{z:.1f}%<extra></extra>", colorbar=dict(title="%")))
        st.plotly_chart(layout(hm, 320), theme=None, width="stretch")

    st.markdown("### Margem por faixa de ticket")
    st.markdown('<p class="msg">O frete é custo fixo por pedido: em tickets baixos ele consome '
                'a margem inteira.</p>', unsafe_allow_html=True)
    ft2 = (df.groupby("faixa_ticket", observed=True)
           .apply(lambda g: pd.Series({"margem": mpct(g), "pedidos": len(g),
                                       "frete": g["custo_frete"].sum() / g["receita_liquida"].sum() * 100}),
                  include_groups=False))
    f3 = go.Figure()
    f3.add_bar(x=ft2.index.astype(str), y=ft2["margem"], name="Margem (%)",
              marker_color=[ERRO if v < 25 else ELO_BLUE for v in ft2["margem"]],
              text=[f"{v:.1f}%" for v in ft2["margem"]], textposition="outside",
              textfont=dict(size=11), hovertemplate="%{x}: %{y:.2f}%<extra></extra>")
    f3.add_scatter(x=ft2.index.astype(str), y=ft2["frete"], name="Frete (% receita)",
                   mode="lines+markers", line=dict(color=MAGENTA, width=3),
                   hovertemplate="Frete: %{y:.2f}%<extra></extra>")
    f3.update_layout(yaxis_title="% da receita líquida", showlegend=True)
    st.plotly_chart(layout(f3, 340), theme=None, width="stretch")

# ======================================================================
# ABA 3 — DESCONTO
# ======================================================================
with t3:
    st.markdown("## O desconto não gera contrapartida em volume")
    st.markdown('<p class="msg">Pedidos com 30% ou mais de desconto levam a mesma quantidade de '
                'itens e têm o mesmo ticket bruto de pedidos sem desconto algum. Só a margem muda.</p>',
                unsafe_allow_html=True)

    fx = (df.groupby("faixa_desconto", observed=True)
          .agg(pedidos=("order_id", "count"), itens=("quantidade", "mean"),
               ticket=("receita_bruta", "mean"), margem=("margem_contribuicao", "mean"),
               desc_total=("desconto_reais", "sum")))

    a, b = st.columns([3, 2], gap="large")
    with a:
        f4 = go.Figure()
        f4.add_bar(x=fx.index.astype(str), y=fx["margem"], name="Margem por pedido (R$)",
                   marker_color=ELO_BLUE, text=[brl(v) for v in fx["margem"]],
                   textposition="outside", textfont=dict(size=10),
                   hovertemplate="Margem: R$ %{y:.2f}<extra></extra>")
        f4.add_scatter(x=fx.index.astype(str), y=fx["itens"], name="Itens por pedido",
                       yaxis="y2", mode="lines+markers", line=dict(color=MAGENTA, width=3),
                       marker=dict(size=9), hovertemplate="Itens: %{y:.2f}<extra></extra>")
        f4.update_layout(
            yaxis=dict(title="Margem por pedido (R$)", range=[0, 560]),
            yaxis2=dict(title="Itens por pedido", overlaying="y", side="right",
                        range=[0, 6], showgrid=False),
            xaxis_title="Faixa de desconto")
        st.plotly_chart(layout(f4, 400), theme=None, width="stretch")
        st.markdown('<p class="nota">A linha de itens permanece plana enquanto a margem cai. '
                    'O desconto não compra volume.</p>', unsafe_allow_html=True)
    with b:
        cd, sd = df[df["tem_desconto"]], df[~df["tem_desconto"]]
        f5 = go.Figure(go.Bar(
            x=["Sem desconto", "Com desconto"], y=[mpct(sd), mpct(cd)],
            marker_color=[ELO_BLUE, MAGENTA],
            text=[f"{mpct(sd):.2f}%", f"{mpct(cd):.2f}%"], textposition="outside",
            textfont=dict(size=15), hovertemplate="%{x}: %{y:.2f}%<extra></extra>"))
        f5.update_layout(yaxis_title="Margem (%)", yaxis_range=[0, 72], showlegend=False,
                         title=dict(text="Margem: com vs. sem desconto"))
        st.plotly_chart(layout(f5, 400), theme=None, width="stretch")
        st.markdown(f'<p class="nota"><b>{brl(DESC25)}</b> concentrados em descontos acima de 25%, '
                    f'em {inteiro(df["desconto_acima_25"].sum())} pedidos.</p>',
                    unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## O desconto cresce nos meses de maior demanda")
    st.markdown('<p class="msg">Novembro concentra o maior volume, o maior desconto e a pior '
                'margem do ano — a promoção é dada justamente quando o cliente já compraria.</p>',
                unsafe_allow_html=True)
    f6 = go.Figure()
    f6.add_bar(x=cal.index, y=cal["idx_pedidos"], name="Índice de volume (média = 100)",
               marker_color=CINZA_CLARO, hovertemplate="Volume: %{y:.0f}<extra></extra>")
    f6.add_scatter(x=cal.index, y=cal["desconto_pct"], name="Desconto (% receita bruta)",
                   yaxis="y2", mode="lines+markers", line=dict(color=MAGENTA, width=3),
                   marker=dict(size=8), hovertemplate="Desconto: %{y:.2f}%<extra></extra>")
    f6.add_scatter(x=cal.index, y=cal["margem_pct"], name="Margem (%)",
                   yaxis="y3", mode="lines+markers",
                   line=dict(color=ELO_BLUE, width=3, dash="dot"), marker=dict(size=8),
                   hovertemplate="Margem: %{y:.2f}%<extra></extra>")
    f6.update_layout(
        yaxis=dict(title="Índice de volume", range=[0, 210]),
        yaxis2=dict(title="Desconto (%)", overlaying="y", side="right", range=[0, 12], showgrid=False),
        yaxis3=dict(overlaying="y", side="right", range=[45, 60], showticklabels=False, showgrid=False))
    st.plotly_chart(layout(f6, 380), theme=None, width="stretch")
    st.markdown('<p class="nota">Base do calendário: 2023, único ano completo.</p>',
                unsafe_allow_html=True)

# ======================================================================
# ABA 4 — FRETE
# ======================================================================
with t4:
    st.markdown("## O frete grátis segue uma regra que exclui o Marketplace")
    st.markdown('<p class="msg">Acima de R$ 250, todos os canais têm frete grátis — exceto o '
                'Marketplace, que paga em 100% dos pedidos.</p>', unsafe_allow_html=True)

    df["grupo_frete"] = "Marketplace"
    fora = df["canal"] != "Marketplace"
    df.loc[fora & (df["receita_liquida"] >= 250), "grupo_frete"] = "Demais canais · ticket ≥ R$ 250"
    df.loc[fora & (df["receita_liquida"] < 250), "grupo_frete"] = "Demais canais · ticket < R$ 250"
    ordem = ["Demais canais · ticket ≥ R$ 250", "Demais canais · ticket < R$ 250", "Marketplace"]
    g = (df.groupby("grupo_frete")
         .agg(pedidos=("order_id", "count"),
              pct_gratis=("frete_gratis", lambda s: s.mean() * 100),
              frete_medio=("custo_frete", "mean")).reindex([o for o in ordem if o in df["grupo_frete"].values]))

    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("### Pedidos com frete grátis")
        f7 = go.Figure(go.Bar(
            y=g.index, x=g["pct_gratis"], orientation="h",
            marker_color=[SUCESSO if v > 50 else ERRO for v in g["pct_gratis"]],
            text=[f"{v:.0f}%" for v in g["pct_gratis"]], textposition="outside",
            textfont=dict(size=14), hovertemplate="%{y}: %{x:.2f}%<extra></extra>"))
        f7.update_layout(xaxis_title="% dos pedidos", xaxis_range=[0, 118], showlegend=False)
        st.plotly_chart(layout(f7, 320), theme=None, width="stretch")
        st.markdown('<p class="nota">A regra é determinística: 100% e 0%, sem meio-termo.</p>',
                    unsafe_allow_html=True)
    with b:
        st.markdown("### Frete como % da receita, por canal")
        fp = (df.groupby("canal")
              .apply(lambda x: x["custo_frete"].sum() / x["receita_liquida"].sum() * 100,
                     include_groups=False).sort_values())
        f8 = go.Figure(go.Bar(
            y=fp.index, x=fp.values, orientation="h",
            marker_color=[MAGENTA if c == "Marketplace" else ELO_BLUE for c in fp.index],
            text=[f"{v:.2f}%" for v in fp.values], textposition="outside",
            textfont=dict(size=11), hovertemplate="%{y}: %{x:.2f}%<extra></extra>"))
        f8.update_layout(xaxis_title="Frete (% da receita)", xaxis_range=[0, 6.4], showlegend=False)
        st.plotly_chart(layout(f8, 320), theme=None, width="stretch")
        st.markdown('<p class="nota">A única variável da base com dispersão relevante entre canais.</p>',
                    unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Onde está o frete não subsidiado")
    mk = df[df["canal"] == "Marketplace"]
    eleg = mk[mk["receita_liquida"] >= 250]
    x, y, z = st.columns(3, gap="medium")
    kpi(x, "Pedidos MK com ticket ≥ R$ 250", inteiro(len(eleg)),
        f"{num(len(eleg)/max(len(mk),1)*100,1)}% do canal — teriam frete grátis em qualquer outro")
    kpi(y, "Frete pago por esses pedidos", brl(FRETE_MK),
        f"+<b>{num(FRETE_MK/R*100)} p.p.</b> de margem se subsidiado", "danger")
    kpi(z, "Frete médio quando cobrado", brl(mk.loc[mk["custo_frete"] > 0, "custo_frete"].mean(), 2),
        f"contra R$ 0,00 nos demais canais acima de R$ 250")

    st.markdown("### Impacto acumulado do frete Marketplace no tempo")
    mkm = (mk[mk["receita_liquida"] >= 250].groupby("ano_mes")["custo_frete"].sum()
           .reindex(sorted(df["ano_mes"].unique()), fill_value=0))
    acc = go.Figure()
    acc.add_bar(x=[pd.to_datetime(m + "-01").strftime("%b/%y") for m in mkm.index], y=mkm.values,
                name="Frete no mês", marker_color=CINZA_CLARO,
                hovertemplate="%{x}: R$ %{y:,.0f}<extra></extra>")
    acc.add_scatter(x=[pd.to_datetime(m + "-01").strftime("%b/%y") for m in mkm.index],
                    y=mkm.cumsum().values, name="Acumulado", mode="lines+markers",
                    line=dict(color=MAGENTA, width=3), hovertemplate="Acum.: R$ %{y:,.0f}<extra></extra>")
    acc.update_layout(yaxis=dict(tickprefix="R$ ", tickformat="~s", title=None))
    st.plotly_chart(layout(acc, 340), theme=None, width="stretch")

# ======================================================================
# ABA 5 — DEVOLUÇÕES & ENTREGA
# ======================================================================
with t5:
    st.markdown("## A devolução transforma margem em prejuízo direto")
    st.markdown(f'<p class="msg">{num(TX_DEV,1)}% dos pedidos voltam. Em cada um, a receita '
                f'evapora mas CMV e frete permanecem — <b>{brl(PERDA_DEV)}</b> no período.</p>',
                unsafe_allow_html=True)

    d1, d2 = st.columns([2, 3], gap="large")
    with d1:
        mot = (df[df["devolvido"]].groupby("motivo_devolucao")
               .agg(pedidos=("order_id", "count"),
                    perda=("custo_produto", "sum")).sort_values("pedidos"))
        mot["perda"] += df[df["devolvido"]].groupby("motivo_devolucao")["custo_frete"].sum()
        fm = go.Figure(go.Bar(
            y=mot.index, x=mot["pedidos"], orientation="h",
            marker_color=[ERRO if "defeito" in m or "Atraso" in m else CINZA_MEDIO for m in mot.index],
            text=[f"{inteiro(p)} · {brl(v)}" for p, v in zip(mot["pedidos"], mot["perda"])],
            textposition="outside", textfont=dict(size=10),
            hovertemplate="%{y}: %{x} pedidos<extra></extra>"))
        fm.update_layout(xaxis_title="Pedidos devolvidos", showlegend=False,
                         xaxis_range=[0, mot["pedidos"].max() * 1.5],
                         title=dict(text="Motivo da devolução"))
        st.plotly_chart(layout(fm, 360), theme=None, width="stretch")
        oper = mot.loc[[m for m in mot.index if "defeito" in m or "Atraso" in m], "pedidos"].sum()
        st.markdown(f'<p class="nota"><b>{num(oper/max(df["devolvido"].sum(),1)*100,0)}%</b> das '
                    f'devoluções têm causa operacional (defeito ou atraso) — endereçável.</p>',
                    unsafe_allow_html=True)
    with d2:
        st.markdown("### Taxa de devolução por canal e categoria")
        dev_piv = df.pivot_table(index="canal", columns="categoria",
                                 values="devolvido", aggfunc="mean") * 100
        hm2 = go.Figure(go.Heatmap(
            z=dev_piv.values, x=dev_piv.columns, y=dev_piv.index,
            colorscale=[[0, "#FFFFFF"], [1, ERRO]],
            text=dev_piv.values, texttemplate="%{text:.1f}%", textfont=dict(size=11),
            hovertemplate="%{y} · %{x}: %{z:.1f}%<extra></extra>", colorbar=dict(title="%")))
        st.plotly_chart(layout(hm2, 360), theme=None, width="stretch")

    st.markdown("---")
    st.markdown("## Prazo de entrega e taxa de devolução")
    st.markdown('<p class="msg">Nas faixas de entrega mais longas a devolução fica ~1,5 p.p. '
                'acima das faixas curtas. O sinal é fraco, mas aponta o SLA como variável a '
                'monitorar.</p>', unsafe_allow_html=True)
    df["_faixa_entrega"] = pd.cut(df["tempo_entrega_real"], [0, 4, 7, 10, 13, 20],
                                  labels=["≤4 dias", "5–7", "8–10", "11–13", "14+"])
    ent = (df.groupby("_faixa_entrega", observed=True)
           .agg(dev=("devolvido", "mean"), pedidos=("order_id", "count"),
                margem=("margem_pct", "mean")))
    fe = go.Figure()
    fe.add_bar(x=ent.index.astype(str), y=ent["pedidos"], name="Pedidos",
               marker_color=CINZA_CLARO, hovertemplate="%{x}: %{y} pedidos<extra></extra>")
    fe.add_scatter(x=ent.index.astype(str), y=ent["dev"] * 100, name="Taxa de devolução (%)",
                   yaxis="y2", mode="lines+markers", line=dict(color=ERRO, width=3),
                   marker=dict(size=9), hovertemplate="Devolução: %{y:.1f}%<extra></extra>")
    fe.update_layout(yaxis_title="Pedidos",
                     yaxis2=dict(title="Taxa de devolução (%)", overlaying="y", side="right",
                                 range=[10, 20], showgrid=False))
    st.plotly_chart(layout(fe, 360), theme=None, width="stretch")

# ======================================================================
# ABA 6 — SIMULADOR
# ======================================================================
with t6:
    st.markdown("## Simulador de rentabilidade")
    st.markdown('<p class="msg">Combine as três alavancas e veja o efeito na margem — cálculo '
                'aplicado sobre o recorte atual de filtros. Nenhuma alavanca mexe em preço ou CMV.</p>',
                unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3, gap="large")
    with s1:
        lev_frete = st.slider("Frete Marketplace ≥ R$ 250 subsidiado", 0, 100, 100, 5,
                              format="%d%%",
                              help="% dos pedidos do Marketplace acima de R$ 250 que passam a ter frete grátis.")
    with s2:
        teto = st.slider("Teto de desconto", 10, 40, 25, 1, format="%d%%",
                         help="Descontos acima deste teto são limitados ao teto.")
        ades_desc = st.slider("Adesão da política de teto", 0, 100, 80, 5, format="%d%%")
    with s3:
        red_dev = st.slider("Redução de devoluções operacionais", 0, 100, 40, 5, format="%d%%",
                            help="% de queda nas devoluções por defeito ou atraso na entrega.")

    ganho_frete = FRETE_MK * (lev_frete / 100)

    mask_teto = df["desconto_pct"] > teto
    ganho_desc = ((df.loc[mask_teto, "desconto_pct"] - teto) / 100
                  * df.loc[mask_teto, "receita_bruta"]).sum() * (ades_desc / 100)

    dev_oper = df[df["devolvido"] & df["motivo_devolucao"].isin(
        ["Produto com defeito", "Atraso na entrega"])]
    ganho_dev = dev_oper[["custo_produto", "custo_frete"]].sum().sum() * (red_dev / 100)

    ganho_margem = ganho_frete + ganho_desc
    M_novo = M + ganho_margem
    margem_nova_pct = M_novo / R * 100
    real_novo_pct = (M_REAL + ganho_margem + ganho_dev) / R_REAL * 100 if R_REAL else np.nan

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4, gap="medium")
    kpi(r1, "Margem de contribuição projetada", f"{num(margem_nova_pct)}%",
        f"de {num(M/R*100)}% &nbsp;→&nbsp; <b>+{num(margem_nova_pct - M/R*100)} p.p.</b>", "ok")
    kpi(r2, "Ganho de margem no período", brl(ganho_margem),
        f"frete {brl(ganho_frete)} + desconto {brl(ganho_desc)}", "ok")
    kpi(r3, "Margem realizada projetada", f"{num(real_novo_pct)}%",
        f"de {num(MARGEM_REAL_PCT)}% &nbsp;→&nbsp; <b>+{num(real_novo_pct - MARGEM_REAL_PCT)} p.p.</b>", "ok")
    kpi(r4, "Devoluções operacionais evitadas", brl(ganho_dev),
        f"{inteiro(len(dev_oper) * red_dev / 100)} pedidos recuperados", "ok")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    # A cascata parte da margem REALIZADA, não da contábil: a alavanca de
    # devoluções só existe nessa definição. Somá-la à margem de contribuição
    # produziria um total que não corresponde a nenhuma das duas métricas.
    M_REAL_PROJ = M_REAL + ganho_margem + ganho_dev
    wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=["Margem realizada atual", "+ Frete MK", "+ Teto desconto",
           "+ Menos devolução", "Margem realizada projetada"],
        y=[M_REAL, ganho_frete, ganho_desc, ganho_dev, M_REAL_PROJ],
        text=[brl(M_REAL), brl(ganho_frete), brl(ganho_desc), brl(ganho_dev), brl(M_REAL_PROJ)],
        textposition="outside", textfont=dict(size=12, color=GRAFITE),
        connector=dict(line=dict(color=CINZA_CLARO)),
        increasing=dict(marker=dict(color=SUCESSO)),
        decreasing=dict(marker=dict(color=MAGENTA)),
        totals=dict(marker=dict(color=ELO_BLUE)),
        hovertemplate="%{x}: %{text}<extra></extra>"))
    wf.update_layout(showlegend=False,
                     yaxis=dict(tickprefix="R$ ", tickformat="~s", title=None),
                     title=dict(text="Ponte da margem realizada — atual → projetada"))
    st.plotly_chart(layout(wf, 420), theme=None, width="stretch")
    st.markdown(f'<p class="nota">As três alavancas somam sobre a margem <b>realizada</b> '
                f'({num(MARGEM_REAL_PCT)}% → {num(real_novo_pct)}%). Sobre a margem de '
                f'contribuição, só frete e desconto se aplicam: {num(M/R*100)}% → '
                f'{num(margem_nova_pct)}%.</p>', unsafe_allow_html=True)

    st.markdown(f"""<p class="nota">
    <b>Premissas.</b> Frete: elimina o custo de frete dos pedidos do Marketplace com receita
    líquida ≥ R$ 250 (elegíveis à regra vigente nos demais canais). Desconto: recupera a parcela
    do desconto que excede o teto, ponderada pela adesão — não assume perda de volume, coerente
    com a evidência da aba Desconto. Devoluções: recupera CMV + frete das devoluções por defeito
    ou atraso, na proporção definida. Valores no período de 13 meses da base.
    </p>""", unsafe_allow_html=True)

# ======================================================================
# RODAPÉ
# ======================================================================
st.markdown(f"<p class='nota' style='margin-top:44px;border-top:1px solid {CINZA_CLARO};"
            f"padding-top:16px'>AI Consulting Lab · Bootcamp EloGroup 2026 — "
            f"margem de contribuição sobre pedidos aprovados. Margem realizada desconta "
            f"devoluções (CMV e frete não retornam). Calendário sazonal com base em 2023, "
            f"único ano completo. Ver sanity checks em tratamento_base_V@.py.</p>",
            unsafe_allow_html=True)
