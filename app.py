"""
Vértice Retail | Painel de rentabilidade comercial
Bootcamp EloGroup 2026

Como rodar:
    pip install -r requirements.txt
    streamlit run app.py

Requer 'vendas_tratada.csv' no mesmo diretório (gerado por tratamento_base_V@.py).
Todos os números, frases de insight e recomendações são calculados a partir dessa
base, sobre o recorte de filtros ativo.
"""

import html
from string import Template

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.colors import sample_colorscale
from plotly.subplots import make_subplots

import elo_agents

# ======================================================================
# PALETA
# ----------------------------------------------------------------------
# Superfícies: os cinco tons roxo-escuros definidos para o painel.
# Cores de dados: tons validados com validate_palette.js no modo escuro,
# contra a superfície dos cartões (#211928): faixa de luminosidade,
# separação para daltonismo entre vizinhos e contraste mínimo de 3:1.
# ======================================================================
PRETO_ARROXEADO = "#1A191E"     # fundo da página
CINZA_MUITO_ESCURO = "#1C191F"  # barra de filtros e navegação
ROXO_ESCURO = "#211928"         # cartões (superfície dos gráficos)
ROXO_PROFUNDO = "#2B1A31"       # elementos elevados: big numbers, campos, recomendações
ROXO_AMEIXA = "#321A3B"         # destaques: aba ativa, trilhas, cabeçalho de tabela

BORDA = "#33243D"
BORDA_FORTE = "#4B3658"
GRADE = "#31243B"
TEXTO = "#F3EEF7"
TEXTO_2 = "#B9AFC4"
TEXTO_3 = "#8F84A0"

VIOLETA = "#8B5CF6"
ROSA = "#EC4899"
CIANO = "#0891B2"
AMBAR = "#D97706"
FUCSIA = "#C026D3"
AZUL = "#3B82F6"
LARANJA = "#EA580C"
LILAS = "#C4B5FD"
ROSA_CLARO = "#F9A8D4"
BOM = "#34D399"
RUIM = "#FB7185"

# Cor fixa por entidade, na ordem validada: um filtro nunca repinta quem sobra.
COR_CANAL = {
    "Google Ads": VIOLETA, "Marketplace": ROSA, "TikTok Ads": CIANO, "Email Marketing": AMBAR,
    "Influenciador": FUCSIA, "Instagram Ads": AZUL, "Orgânico": LARANJA,
}
COR_CATEGORIA = {"Moda": VIOLETA, "Beleza": ROSA, "Lifestyle": CIANO, "Acessórios": AMBAR}
COR_PAGAMENTO = {"Cartão de Crédito": VIOLETA, "PIX": ROSA, "Boleto": CIANO, "Vale-Troca": AMBAR}
CORES_DIM = {"canal": COR_CANAL, "categoria": COR_CATEGORIA, "metodo_pagamento": COR_PAGAMENTO}
TEMA_COR = {"Frete": CIANO, "Desconto": ROSA, "Ticket": AMBAR, "Devolução": FUCSIA, "Sazonalidade": AZUL,
            "Canais": VIOLETA, "Mix": LARANJA, "Operação": AZUL, "Margem": VIOLETA, "Receita": AZUL,
            "Volume": CIANO, "Prazo": AMBAR, "Categoria": ROSA, "Pagamento": LARANJA, "Produto": FUCSIA,
            "Atendimento": CIANO, "Estoque": LARANJA}

COR_BASE = VIOLETA   # série única
COR_FOCO = ROSA      # entidade em destaque numa série única
COR_NEUTRA = "#6B5A7B"
ESCALA_SEQ = [[0, "#7453D6"], [0.35, "#9270F5"], [0.7, "#B9A2FF"], [1, "#E4DAFF"]]
ESCALA_DIV = [[0, ROSA], [0.5, "#5A4D66"], [1, CIANO]]

H_P, H_M, H_G = 280, 330, 380  # alturas padrão dos gráficos

st.set_page_config(page_title="Vértice Retail | Rentabilidade", layout="wide",
                   initial_sidebar_state="collapsed")

CSS = Template("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root { color-scheme: dark; }
.stApp { background-color: $PRETO_ARROXEADO !important; color: $TEXTO !important;
   background-image: radial-gradient(900px 440px at 6% -10%, rgba(139,92,246,.20), transparent 62%),
                     radial-gradient(760px 400px at 102% -4%, rgba(236,72,153,.13), transparent 60%) !important;
   background-attachment: fixed !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
   background: transparent !important; color: $TEXTO !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] svg { fill: $TEXTO_3 !important; }
.block-container { padding: 1.3rem 2rem 2.5rem !important; max-width: 1560px; }
html, body, [class*="css"], [data-testid="stMarkdownContainer"], button, input, textarea {
   font-family: 'Inter', Helvetica, Arial, sans-serif !important; }
[data-testid="stMarkdownContainer"] p { color: $TEXTO_2; }
/* O Streamlit aplica margin-bottom:-16px ao bloco de markdown para compensar a margem de um
   parágrafo. Aqui todo markdown é HTML próprio em div, sem essa margem: sem o reset, subtítulos,
   notas e caixas de insight ficam 16px sobrepostos ao elemento seguinte.
   ATENÇÃO: não usar sinais de menor/maior neste bloco; o sanitizador do st.html os lê como tags
   e descarta o estilo inteiro. */
[data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0.85rem; }

/* cabeçalho */
.topo { display:flex; justify-content:space-between; align-items:center; gap:24px; padding: 2px 2px 4px; }
.marca { display:flex; align-items:center; gap:14px; }
.logo { width:44px; height:44px; border-radius:12px; display:flex; align-items:center; justify-content:center;
   background: linear-gradient(135deg, $VIOLETA 0%, $ROSA 100%); color:#FFFFFF; font-weight:800; font-size:20px;
   box-shadow: 0 8px 24px rgba(139,92,246,.35); }
.topo .titulo { font-size: 22px; font-weight: 700; color: $TEXTO; letter-spacing: -0.02em; }
.topo .titulo span { background: linear-gradient(90deg, $LILAS, $ROSA_CLARO); -webkit-background-clip: text;
   background-clip: text; color: transparent; }
.topo .sub { font-size: 13px; color: $TEXTO_3; margin-top: 2px; }
.meta { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.pilula { display:inline-flex; align-items:center; gap:8px; font-size:12px; color:$TEXTO_2; background:$ROXO_PROFUNDO;
   border:1px solid $BORDA; border-radius:999px; padding:6px 12px; }
.ponto { width:7px; height:7px; border-radius:50%; background:$BOM; box-shadow:0 0 0 3px rgba(52,211,153,.18); }

/* cartões */
div[class*="st-key-card_"] { background: linear-gradient(180deg, rgba(50,26,59,.45) 0%, rgba(33,25,40,0) 140px), $ROXO_ESCURO;
   border: 1px solid $BORDA; border-radius: 14px; padding: 16px 18px 14px; gap: .6rem;
   box-shadow: inset 0 1px 0 rgba(255,255,255,.03), 0 12px 32px rgba(0,0,0,.28); }
[data-testid="stColumn"] div[class*="st-key-card_"] { height: 100%; }
div[class*="st-key-card_filtros"] { background: $CINZA_MUITO_ESCURO; border-radius: 12px; padding: 10px 16px 12px; }
.card-titulo { font-size: 15px; font-weight: 600; color: $TEXTO; line-height: 1.35; display:flex; align-items:center; gap:9px; }
.card-titulo::before { content:""; flex: 0 0 8px; height:8px; border-radius:2px; background: linear-gradient(135deg, $VIOLETA, $ROSA); }
.card-sub { font-size: 12px; color: $TEXTO_3; margin-top: 3px; line-height: 1.4; }

/* big numbers */
.kpi { display:flex; flex-direction:column; background: linear-gradient(160deg, $ROXO_PROFUNDO 0%, $ROXO_ESCURO 100%);
   border:1px solid $BORDA; border-radius:14px; padding:14px 16px 10px; min-height:160px; overflow:hidden; }
.kpi-topo { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.kpi-rotulo { font-size:12px; font-weight:500; color:$TEXTO_2; }
.icone { flex: 0 0 30px; height:30px; border-radius:9px; display:flex; align-items:center; justify-content:center;
   background: rgba(139,92,246,.16); color:$LILAS; }
.icone svg { width:16px; height:16px; }
.kpi-valor { font-size:28px; font-weight:700; color:$TEXTO; line-height:1.15; margin-top:8px; white-space:nowrap; letter-spacing:-0.02em; }
.kpi-linha { display:flex; align-items:center; gap:8px; margin: 4px 0 8px; font-size:12px; color:$TEXTO_3; flex-wrap:wrap; }
.delta { display:inline-flex; align-items:center; gap:3px; font-size:11px; font-weight:600; border-radius:999px; padding:2px 8px; }
.delta.bom { color:$BOM; background: rgba(52,211,153,.12); }
.delta.ruim { color:$RUIM; background: rgba(251,113,133,.12); }
.delta.neutro { color:$TEXTO_2; background: rgba(185,175,196,.10); }
.spark { display:block; margin-top:auto; width:100%; height:34px; }

/* insight */
.insight { background: linear-gradient(135deg, rgba(139,92,246,.17) 0%, rgba(236,72,153,.07) 100%);
   border:1px solid rgba(139,92,246,.32); border-radius:10px; padding:11px 14px; }
.insight .rot { display:flex; align-items:center; gap:6px; font-size:11px; font-weight:700; color:$LILAS; letter-spacing:.06em; text-transform:uppercase; }
.insight .rot svg { width:13px; height:13px; }
.insight .txt { font-size:13px; color:$TEXTO; margin-top:4px; line-height:1.55; }
.insight .acao { font-size:13px; color:$TEXTO_2; margin-top:6px; line-height:1.5; }
.insight .acao b { color:$ROSA_CLARO; font-weight:600; }

/* recomendações */
.recs { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
@media (max-width: 1100px) { .recs { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 700px) { .recs { grid-template-columns: 1fr; } }
.rec { border:1px solid $BORDA; border-radius:12px; padding:14px 16px; display:flex; flex-direction:column; gap:8px;
   background: linear-gradient(180deg, $ROXO_PROFUNDO 0%, $ROXO_ESCURO 100%); }
.rec-topo { display:flex; align-items:center; gap:10px; }
.rank { flex: 0 0 30px; height:30px; border-radius:9px; display:flex; align-items:center; justify-content:center;
   font-size:12px; font-weight:800; color:#FFFFFF; background: linear-gradient(135deg, $VIOLETA, $ROSA); }
.tema { font-size:11px; font-weight:600; color:$TEXTO; border-radius:999px; padding:3px 10px; }
.rec-aba { margin-left:auto; font-size:11px; color:$TEXTO_3; white-space:nowrap; }
.rec-titulo { font-size:14px; font-weight:600; color:$TEXTO; line-height:1.35; }
.rec-texto { font-size:13px; color:$TEXTO_2; line-height:1.55; }
.rec-valor { display:flex; align-items:baseline; gap:6px; font-size:12px; color:$TEXTO_3; flex-wrap:wrap; }
.rec-valor b { font-size:20px; font-weight:700; color:$TEXTO; letter-spacing:-.01em; }
.medidor { height:6px; border-radius:999px; background:$ROXO_AMEIXA; overflow:hidden; }
.medidor span { display:block; height:100%; border-radius:999px; background: linear-gradient(90deg, $VIOLETA, $ROSA); }
.rec-acao { font-size:13px; color:$TEXTO; line-height:1.5; border-top:1px solid $BORDA; padding-top:8px; margin-top:auto; }
.rec-acao b { color:$ROSA_CLARO; font-weight:600; }

/* peças auxiliares */
.nota { font-size:12px; color:$TEXTO_3 !important; line-height:1.45; }
.chip { display:inline-flex; align-items:center; gap:6px; font-size:12px; color:$TEXTO; background:$ROXO_AMEIXA;
   border:1px solid $BORDA_FORTE; border-radius:999px; padding:5px 12px; }
.stats { display:flex; flex-wrap:wrap; gap:10px; }
.stat { background:$ROXO_PROFUNDO; border:1px solid $BORDA; border-radius:10px; padding:10px 14px; min-width:190px; }
.stat .r { font-size:11px; color:$TEXTO_3; }
.stat .v { font-size:18px; font-weight:700; color:$TEXTO; margin:2px 0; }
.legenda-div { display:flex; align-items:center; gap:10px; font-size:11px; color:$TEXTO_3; margin-top:2px; }
.barra-div { flex:1; height:8px; border-radius:999px; background: linear-gradient(90deg, $ROSA, #5A4D66, #0891B2); }

/* insights do Elo Agents */
.aviso { background: rgba(217,119,6,.10); border:1px solid rgba(217,119,6,.35); border-radius:10px; padding:11px 14px; }
.aviso b { color:#FBBF24; font-size:13px; font-weight:600; }
.aviso div { font-size:13px; color:$TEXTO_2; margin-top:3px; line-height:1.5; }
.aviso.erro { background: rgba(251,113,133,.10); border-color: rgba(251,113,133,.35); }
.aviso.erro b { color:$RUIM; }
.ia-meta { display:flex; flex-wrap:wrap; align-items:center; gap:8px; font-size:12px; color:$TEXTO_3; }
.selo { display:inline-flex; align-self:flex-start; align-items:center; font-size:11px; font-weight:600;
   border-radius:999px; padding:3px 9px; line-height:1.4; }
.selo.ok { color:$BOM; background: rgba(52,211,153,.10); border:1px solid rgba(52,211,153,.30); }
.selo.alerta { color:#FBBF24; background: rgba(217,119,6,.12); border:1px solid rgba(217,119,6,.35); }
.subtitulo-recs { font-size:12px; font-weight:600; color:$TEXTO_2; letter-spacing:.04em; text-transform:uppercase; }

/* navegação: nesta versão do Streamlit as abas usam react-aria (role tablist e data-testid stTab), sem baseweb */
[data-testid="stTabs"] { margin-top: 6px; }
[data-testid="stTabs"] [role="tablist"] { display:inline-flex !important; gap:4px; width:auto !important;
   background:$CINZA_MUITO_ESCURO !important; border:1px solid $BORDA !important; border-radius:12px; padding:5px;
   box-shadow:none !important; }
[data-testid="stTabs"] [role="tablist"]::before, [data-testid="stTabs"] [role="tablist"]::after { display:none !important; }
[data-testid="stTabs"] > div:first-child { border-bottom:none !important; box-shadow:none !important; }
[data-testid="stTab"] { background:transparent !important; color:$TEXTO_3 !important; padding:8px 14px !important;
   border-radius:8px !important; border:none !important; }
[data-testid="stTab"] p { color:inherit !important; font-weight:600 !important; font-size:13.5px !important; }
[data-testid="stTab"]:hover { color:$TEXTO !important; background: rgba(139,92,246,.10) !important; }
[data-testid="stTab"][aria-selected="true"] { color:$TEXTO !important;
   background: linear-gradient(135deg, rgba(139,92,246,.38), rgba(236,72,153,.22)) !important;
   box-shadow: inset 0 0 0 1px rgba(196,181,253,.25) !important; }
[data-testid="stTabs"] [role="tabpanel"] { padding-top: 14px; }

/* controles */
[data-testid="stWidgetLabel"] p { color:$TEXTO_2 !important; font-weight:500 !important; font-size:12px !important; }
[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="base-input"] {
   background-color:$ROXO_PROFUNDO !important; border-color:$BORDA !important; color:$TEXTO !important; border-radius:9px !important; }
[data-baseweb="input"] input, [data-baseweb="base-input"] input { color:$TEXTO_2 !important; -webkit-text-fill-color:$TEXTO_2 !important; }
[data-baseweb="select"] svg { fill:$TEXTO_3 !important; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"], [data-baseweb="menu"] li {
   background-color:$ROXO_PROFUNDO !important; color:$TEXTO !important; }
[data-baseweb="menu"] li:hover { background-color:$ROXO_AMEIXA !important; }
[data-baseweb="tag"] { background-color: rgba(139,92,246,.24) !important; border:none !important; }
[data-baseweb="tag"] span { color:$TEXTO !important; }
[data-baseweb="tag"] svg { fill:$LILAS !important; }
[data-testid="stSlider"] [role="slider"] { background-color:$VIOLETA !important; box-shadow: 0 0 0 4px rgba(139,92,246,.25) !important; }
[data-testid="stThumbValue"] { color:$LILAS !important; font-weight:600 !important; }
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] { color:$TEXTO_3 !important; background:transparent !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:$TEXTO_3 !important; }
[data-testid="stCheckbox"] p, [data-testid="stToggle"] p { color:$TEXTO_2 !important; font-size:13px !important; }
[data-testid="stExpander"] details { background:$ROXO_ESCURO !important; border:1px solid $BORDA !important; border-radius:12px !important; }
[data-testid="stExpander"] summary p { color:$TEXTO_2 !important; }
.stDownloadButton button, .stButton button { background:$ROXO_PROFUNDO !important; border:1px solid $BORDA_FORTE !important;
   color:$TEXTO !important; border-radius:9px !important; }
.stDownloadButton button:hover, .stButton button:hover { border-color:$VIOLETA !important; color:$LILAS !important; }
.stButton button[data-testid="stBaseButton-primary"] { background: linear-gradient(135deg, $VIOLETA 0%, $ROSA 100%) !important;
   border:none !important; color:#FFFFFF !important; font-weight:600 !important; box-shadow: 0 6px 18px rgba(139,92,246,.30); }
.stButton button[data-testid="stBaseButton-primary"]:hover { color:#FFFFFF !important; filter: brightness(1.08); }
.modebar { background: transparent !important; }
</style>
""").substitute(
    PRETO_ARROXEADO=PRETO_ARROXEADO, CINZA_MUITO_ESCURO=CINZA_MUITO_ESCURO, ROXO_ESCURO=ROXO_ESCURO,
    ROXO_PROFUNDO=ROXO_PROFUNDO, ROXO_AMEIXA=ROXO_AMEIXA, BORDA=BORDA, BORDA_FORTE=BORDA_FORTE,
    TEXTO=TEXTO, TEXTO_2=TEXTO_2, TEXTO_3=TEXTO_3, VIOLETA=VIOLETA, ROSA=ROSA, LILAS=LILAS,
    ROSA_CLARO=ROSA_CLARO, BOM=BOM, RUIM=RUIM,
)
st.html(CSS)


# ======================================================================
# FORMATAÇÃO E ÍCONES
# ======================================================================
MES_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MES_EXTENSO = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
               "setembro", "outubro", "novembro", "dezembro"]


def num(v, casas=1):
    if v is None or pd.isna(v):
        return "–"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def inteiro(v):
    return num(v, 0)


def brl(v, casas=0):
    return ("-" if v < 0 else "") + "R$ " + num(abs(v), casas)


def brl_c(v):
    """R$ compacto: 16,67 mi / 305,5 mil / 950."""
    a, s = abs(v), "-" if v < 0 else ""
    if a >= 1e6:
        return f"{s}R$ {num(a / 1e6, 2)} mi"
    if a >= 1e4:
        return f"{s}R$ {num(a / 1e3, 1)} mil"
    return f"{s}R$ {num(a, 0)}"


def pct(v, casas=1):
    return f"{num(v, casas)}%"


def esc(s):
    return html.escape(str(s))


def mes_rotulo(ano_mes, extenso=False):
    p = pd.Period(ano_mes, "M")
    nomes = MES_EXTENSO if extenso else MES_ABREV
    return f"{nomes[p.month - 1]}/{p.year % 100:02d}"


def _svg(corpo):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{corpo}</svg>')


ICONES = {
    "receita": _svg('<polyline points="3 17 9 11 13 15 21 7"></polyline><polyline points="14 7 21 7 21 14"></polyline>'),
    "margem": _svg('<line x1="19" y1="5" x2="5" y2="19"></line><circle cx="6.5" cy="6.5" r="2.5"></circle>'
                   '<circle cx="17.5" cy="17.5" r="2.5"></circle>'),
    "realizada": _svg('<circle cx="12" cy="12" r="9"></circle><polyline points="8 12 11 15 16 9"></polyline>'),
    "pedidos": _svg('<path d="M3 7l9-4 9 4-9 4-9-4z"></path><path d="M3 7v10l9 4 9-4V7"></path><path d="M12 11v10"></path>'),
    "ticket": _svg('<rect x="2" y="5" width="20" height="14" rx="2"></rect><line x1="2" y1="10" x2="22" y2="10"></line>'),
    "devolucao": _svg('<path d="M3 12a9 9 0 1 0 3-6.7"></path><polyline points="3 3 3 9 9 9"></polyline>'),
    "insight": _svg('<path d="M9 18h6"></path><path d="M10 22h4"></path>'
                    '<path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.3h6c0-1 .4-1.8 1-2.3A7 7 0 0 0 12 2z"></path>'),
}


def sparkline(valores, chave, cor=VIOLETA):
    """Minigráfico SVG da tendência; o último ponto em destaque."""
    v = [float(x) for x in valores if pd.notna(x)]
    if len(v) < 2:
        return ""
    w, h, p = 200, 34, 4
    lo, hi = min(v), max(v)
    amp = (hi - lo) or 1
    xs = [p + i * (w - 2 * p) / (len(v) - 1) for i in range(len(v))]
    ys = [h - p - (x - lo) / amp * (h - 2 * p) for x in v]
    pontos = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"M{xs[0]:.1f},{h} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys)) + f" L{xs[-1]:.1f},{h} Z"
    gid = f"spark_{chave}"
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{cor}" stop-opacity="0.45"></stop>'
            f'<stop offset="1" stop-color="{cor}" stop-opacity="0"></stop></linearGradient></defs>'
            f'<path d="{area}" fill="url(#{gid})"></path>'
            f'<polyline points="{pontos}" fill="none" stroke="{cor}" stroke-width="2" vector-effect="non-scaling-stroke"></polyline>'
            f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3" fill="{ROSA}"></circle></svg>')


# ======================================================================
# MÉTRICAS
# ======================================================================
SOMAS = dict(
    receita=("receita_liquida", "sum"), receita_bruta=("receita_bruta", "sum"),
    margem=("margem_contribuicao", "sum"), cmv=("custo_produto", "sum"),
    frete=("custo_frete", "sum"), desconto=("desconto_reais", "sum"),
    pedidos=("order_id", "count"), itens=("quantidade", "sum"), devolvidos=("devolvido", "sum"),
    margem_real=("margem_realizada", "sum"), receita_real=("receita_realizada", "sum"),
    negativos=("margem_negativa", "sum"), prazo_soma=("tempo_entrega_real", "sum"),
)


def _div(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return np.divide(a, b, out=np.full_like(a, np.nan), where=b != 0)


def agregar(d, por=None):
    """Somas por grupo e razões derivadas das somas (nunca média de percentuais)."""
    if por is None:
        t = d.assign(_todos=1).groupby("_todos").agg(**SOMAS)
    else:
        t = d.groupby(por, observed=True).agg(**SOMAS)
    t["margem_pct"] = _div(t["margem"], t["receita"]) * 100
    t["margem_real_pct"] = _div(t["margem_real"], t["receita_real"]) * 100
    t["ticket"] = _div(t["receita"], t["pedidos"])
    t["itens_pedido"] = _div(t["itens"], t["pedidos"])
    t["desconto_pct"] = _div(t["desconto"], t["receita_bruta"]) * 100
    t["frete_pct"] = _div(t["frete"], t["receita"]) * 100
    t["cmv_pct"] = _div(t["cmv"], t["receita"]) * 100
    t["taxa_dev"] = _div(t["devolvidos"], t["pedidos"]) * 100
    t["prazo"] = _div(t["prazo_soma"], t["pedidos"])
    return t


METRICAS = {
    "receita": dict(nome="Receita líquida", tipo="brl", melhor=1),
    "margem": dict(nome="Margem de contribuição (R$)", tipo="brl", melhor=1),
    "margem_pct": dict(nome="Margem de contribuição (%)", tipo="pct", melhor=1),
    "margem_real_pct": dict(nome="Margem realizada (%)", tipo="pct", melhor=1),
    "pedidos": dict(nome="Pedidos", tipo="int", melhor=1),
    "ticket": dict(nome="Ticket médio", tipo="brl2", melhor=1),
    "itens_pedido": dict(nome="Itens por pedido", tipo="dec", melhor=0),
    "desconto_pct": dict(nome="Desconto (% da receita bruta)", tipo="pct", melhor=-1),
    "desconto": dict(nome="Desconto concedido (R$)", tipo="brl", melhor=-1),
    "frete_pct": dict(nome="Frete (% da receita)", tipo="pct", melhor=-1),
    "frete": dict(nome="Frete pago (R$)", tipo="brl", melhor=-1),
    "cmv_pct": dict(nome="CMV (% da receita)", tipo="pct", melhor=-1),
    "taxa_dev": dict(nome="Taxa de devolução (%)", tipo="pct", melhor=-1),
    "prazo": dict(nome="Prazo médio de entrega (dias)", tipo="dec", melhor=-1),
    "negativos": dict(nome="Pedidos com margem negativa", tipo="int", melhor=-1),
}
ADITIVAS = {"receita", "margem", "pedidos", "desconto", "frete", "negativos"}


def fmt(v, tipo):
    return {"brl": brl_c, "brl2": lambda x: brl(x, 2), "pct": pct, "int": inteiro,
            "dec": lambda x: num(x, 2)}[tipo](v)


def hover_num(tipo, eixo):
    return {"brl": f"R$ %{{{eixo}:,.0f}}", "brl2": f"R$ %{{{eixo}:,.2f}}", "pct": f"%{{{eixo}:.1f}}%",
            "int": f"%{{{eixo}:,.0f}}", "dec": f"%{{{eixo}:.2f}}"}[tipo]


def eixo_fmt(tipo):
    if tipo in ("brl", "brl2"):
        return dict(tickprefix="R$ ", tickformat="~s")
    if tipo == "pct":
        return dict(ticksuffix="%", tickformat=".0f")
    if tipo == "int":
        return dict(tickformat="~s")
    return dict(tickformat=".1f")


# ======================================================================
# GRÁFICOS: padrão único
# ======================================================================
def estilo(fig, altura=H_M, horizontal=False, legenda=False):
    fig.update_layout(
        height=altura, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Helvetica, Arial, sans-serif", size=12, color=TEXTO_2),
        margin=dict(l=4, r=24, t=34 if legenda else 10, b=6),
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, xanchor="left",
                    font=dict(size=12, color=TEXTO_2), bgcolor="rgba(0,0,0,0)", title=None),
        hoverlabel=dict(bgcolor=ROXO_AMEIXA, bordercolor=BORDA_FORTE,
                        font=dict(color=TEXTO, size=12, family="Inter, Helvetica, Arial")),
        separators=",.", bargap=0.38, barcornerradius=6, title=None,
    )
    grade = dict(showgrid=True, gridcolor=GRADE, gridwidth=1, zeroline=False)
    sem_grade = dict(showgrid=False, zeroline=False)
    comum = dict(automargin=True, tickfont=dict(size=11, color=TEXTO_3),
                 title_font=dict(size=12, color=TEXTO_3), showline=False, ticks="")
    fig.update_xaxes(**comum, **(grade if horizontal else sem_grade))
    fig.update_yaxes(**comum, **(sem_grade if horizontal else grade))
    if horizontal:
        fig.update_yaxes(tickfont=dict(size=12, color=TEXTO_2))
    fig.update_traces(cliponaxis=False, selector=dict(type="bar"))
    fig.update_traces(cliponaxis=False, selector=dict(type="waterfall"))
    return fig


# Sem a barra de ícones do Plotly: ela cobria rótulos das barras do topo. Tela cheia continua
# disponível pelo menu do próprio Streamlit ao passar o mouse no gráfico.
CONFIG_PLOTLY = {"displaylogo": False, "displayModeBar": False}


def plot(fig, key=None, selecionavel=False):
    return st.plotly_chart(fig, theme=None, width="stretch", config=CONFIG_PLOTLY, key=key,
                           on_select="rerun" if selecionavel else "ignore")


def card(chave):
    return st.container(key=f"card_{chave}")


def cabecalho(titulo, sub=None):
    st.markdown(f'<div class="card-titulo">{esc(titulo)}</div>'
                + (f'<div class="card-sub">{esc(sub)}</div>' if sub else ""), unsafe_allow_html=True)


def insight(texto, acao=None, rotulo="Insight"):
    if not texto:
        return
    st.markdown(f'<div class="insight"><div class="rot">{ICONES["insight"]}{esc(rotulo)}</div>'
                f'<div class="txt">{esc(texto)}</div>'
                + (f'<div class="acao"><b>Ação recomendada:</b> {esc(acao)}</div>' if acao else "")
                + '</div>', unsafe_allow_html=True)


def nota(texto):
    st.markdown(f'<div class="nota">{esc(texto)}</div>', unsafe_allow_html=True)


def csv_bytes(d):
    return d.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def pontos_selecionados(evento):
    try:
        return list(evento["selection"]["points"])
    except (KeyError, TypeError):
        return []


def barras_h(t, col, tipo, foco=None, altura=None, rotulos=True, customdata=None):
    """Barras horizontais de série única, maior valor no topo, foco opcional em rosa."""
    t = t.sort_values(col)
    fig = go.Figure(go.Bar(
        y=t.index.astype(str), x=t[col], orientation="h",
        marker_color=[COR_FOCO if foco is not None and i in foco else COR_BASE for i in t.index],
        text=[fmt(v, tipo) for v in t[col]] if rotulos else None, textposition="outside",
        textfont=dict(size=11, color=TEXTO_2),
        customdata=customdata if customdata is not None else t.index.astype(str),
        hovertemplate="<b>%{y}</b><br>" + hover_num(tipo, "x") + "<extra></extra>"))
    maximo = np.nanmax(t[col].values) if len(t) else 1
    fig.update_xaxes(range=[0, maximo * 1.22 if maximo > 0 else 1], **eixo_fmt(tipo))
    return estilo(fig, altura or max(H_P - 40, 34 * len(t) + 40), horizontal=True)


def colunas(x, y, tipo, foco=None, altura=H_P, rotulos=True, hover_extra=None):
    """Colunas de série única em ordem natural (faixas, meses)."""
    fig = go.Figure(go.Bar(
        x=list(x), y=list(y),
        marker_color=[COR_FOCO if foco is not None and xi in foco else COR_BASE for xi in x],
        text=[fmt(v, tipo) for v in y] if rotulos else None, textposition="outside",
        textfont=dict(size=11, color=TEXTO_2),
        customdata=hover_extra,
        hovertemplate="<b>%{x}</b><br>" + hover_num(tipo, "y")
        + ("<br>%{customdata}" if hover_extra is not None else "") + "<extra></extra>"))
    maximo = np.nanmax(list(y)) if len(y) else 1
    fig.update_yaxes(range=[0, maximo * 1.2 if maximo > 0 else 1], **eixo_fmt(tipo))
    return estilo(fig, altura)


# ======================================================================
# DADOS
# ======================================================================
def rotular_celulas(fig, z, xs, ys, formato):
    """Rótulo por célula de heatmap com a cor escolhida pelo fundo: tinta escura nas células
    claras, branca nas escuras (o Plotly usa uma cor só e some nas células claras)."""
    zz = np.asarray(z, dtype=float)
    lo, hi = np.nanmin(zz), np.nanmax(zz)
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            v = zz[i, j]
            if np.isnan(v):
                continue
            claro = (v - lo) / ((hi - lo) or 1) > 0.6
            fig.add_annotation(x=x, y=y, text=formato(v), showarrow=False,
                               font=dict(size=11, color=PRETO_ARROXEADO if claro else "#FFFFFF"))
    return fig


ORDEM_TICKET = ["<100", "100-200", "200-250", "250-300", "300-500", "500-1000", ">1000"]
ROTULO_TICKET = {"<100": "Até R$ 100", "100-200": "R$ 100–200", "200-250": "R$ 200–250",
                 "250-300": "R$ 250–300", "300-500": "R$ 300–500", "500-1000": "R$ 500–1.000",
                 ">1000": "Acima de R$ 1.000"}
ORDEM_DESCONTO = ["0%", "0-10%", "10-20%", "20-25%", "25-30%", ">30%"]
ROTULO_DESCONTO = {"0%": "Sem desconto", "0-10%": "Até 10%", "10-20%": "10–20%", "20-25%": "20–25%",
                   "25-30%": "25–30%", ">30%": "Acima de 30%"}
ORDEM_PRAZO = ["Até 4 dias", "5 a 7 dias", "8 a 10 dias", "11 a 13 dias", "14 dias ou mais"]
OPERACIONAIS = ["Produto com defeito", "Atraso na entrega"]


@st.cache_data
def carregar():
    # O CSV perde o tipo Categorical: sem isto as faixas voltam em ordem alfabética.
    d = pd.read_csv("vendas_tratada.csv", parse_dates=["data_pedido"])
    d["dia"] = d["data_pedido"].dt.normalize()
    d["faixa_ticket"] = pd.Categorical(d["faixa_ticket"].map(ROTULO_TICKET),
                                       [ROTULO_TICKET[k] for k in ORDEM_TICKET], ordered=True)
    d["faixa_desconto"] = pd.Categorical(d["faixa_desconto"].map(ROTULO_DESCONTO),
                                         [ROTULO_DESCONTO[k] for k in ORDEM_DESCONTO], ordered=True)
    d["faixa_prazo"] = pd.cut(d["tempo_entrega_real"], [0, 4, 7, 10, 13, 99], labels=ORDEM_PRAZO)
    d["mes_rotulo"] = pd.Categorical(
        d["ano_mes"].map(mes_rotulo), [mes_rotulo(m) for m in sorted(d["ano_mes"].unique())], ordered=True)
    return d


BASE = carregar()
DATA_MIN, DATA_MAX = BASE["dia"].min(), BASE["dia"].max()
# Colunas do cadastro de estoque só existem se o tratamento rodou com PROCESSAR_OUTRAS_BASES.
TEM_ESTOQUE = "subcategoria" in BASE.columns


@st.cache_data
def carregar_atendimento():
    # Chamados do SAC. Só por data, canal de entrada e motivo: o vínculo com o pedido não é confiável
    # (a maioria dos order_id não existe em vendas e parte dos chamados abre antes do pedido).
    try:
        a = pd.read_csv("atendimento_tratado.csv", parse_dates=["data_abertura"], usecols=[
            "ticket_id", "data_abertura", "canal_entrada", "categoria_problema", "status_atendimento",
            "nota_csat", "tempo_primeira_resposta_minutos", "custo_operacional_ticket", "pendente"])
    except (FileNotFoundError, ValueError):
        return None
    a["dia"] = a["data_abertura"].dt.normalize()
    return a


ATD = carregar_atendimento()


def tabelas_atendimento(a):
    """Agregados do SAC por canal de entrada e por motivo, com participações já calculadas."""
    pc = a.groupby("canal_entrada").agg(
        chamados=("ticket_id", "count"), custo=("custo_operacional_ticket", "sum"), csat=("nota_csat", "mean"),
        resposta_min=("tempo_primeira_resposta_minutos", "median"), pendentes=("pendente", "sum"))
    pc["custo_chamado"] = pc["custo"] / pc["chamados"]
    pc["part_chamados"] = pc["chamados"] / pc["chamados"].sum() * 100
    pc["part_custo"] = pc["custo"] / pc["custo"].sum() * 100
    pm = a.groupby("categoria_problema").agg(chamados=("ticket_id", "count"), csat=("nota_csat", "mean"),
                                             pendentes=("pendente", "sum"))
    pm["part_chamados"] = pm["chamados"] / pm["chamados"].sum() * 100
    return pc, pm


# ======================================================================
# CABEÇALHO E FILTROS
# ======================================================================
st.markdown(
    '<div class="topo"><div class="marca"><div class="logo">V</div><div>'
    '<div class="titulo">Vértice Retail · <span>Rentabilidade comercial</span></div>'
    '<div class="sub">Receita, margem, desconto, frete e devoluções dos pedidos aprovados</div></div></div>'
    f'<div class="meta"><span class="pilula"><span class="ponto"></span>Dados até {DATA_MAX:%d/%m/%Y}</span>'
    f'<span class="pilula">Desde {DATA_MIN:%d/%m/%Y}</span>'
    f'<span class="pilula">{inteiro(len(BASE))} pedidos aprovados</span></div></div>',
    unsafe_allow_html=True)

PRESETS = ["Todo o período", "Últimos 30 dias", "Últimos 90 dias", "Ano de 2023", "Personalizado"]
st.session_state.setdefault("versao_drill", 0)
CHAVE_DRILL = f"drill_canal_{st.session_state['versao_drill']}"

with card("filtros"):
    f = st.columns([1.15, 1.35, 1.5, 1.3, 1.3, 0.95], gap="small", vertical_alignment="bottom")
    preset = f[0].selectbox("Período", PRESETS, key="f_periodo")
    if preset == "Personalizado":
        faixa = f[1].date_input("Datas", value=(DATA_MIN.date(), DATA_MAX.date()), min_value=DATA_MIN.date(),
                                max_value=DATA_MAX.date(), format="DD/MM/YYYY", key="f_datas")
        ini = pd.Timestamp(faixa[0])
        fim = pd.Timestamp(faixa[1]) if len(faixa) > 1 else ini
    else:
        ini, fim = {
            "Todo o período": (DATA_MIN, DATA_MAX),
            "Últimos 30 dias": (DATA_MAX - pd.Timedelta(days=29), DATA_MAX),
            "Últimos 90 dias": (DATA_MAX - pd.Timedelta(days=89), DATA_MAX),
            "Ano de 2023": (pd.Timestamp("2023-01-01"), pd.Timestamp("2023-12-31")),
        }[preset]
        f[1].text_input("Datas", value=f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y}", disabled=True, key="f_datas_txt")
    canais_sel = f[2].multiselect("Canal", list(COR_CANAL), placeholder="Todos", key="f_canal")
    cats_sel = f[3].multiselect("Categoria", list(COR_CATEGORIA), placeholder="Todas", key="f_cat")
    pgto_sel = f[4].multiselect("Pagamento", list(COR_PAGAMENTO), placeholder="Todos", key="f_pgto")
    incluir_dev = f[5].toggle("Incluir devolvidos", value=True, key="f_dev")

# Seleção feita no gráfico "Margem por canal" (filtro cruzado, como no Power BI).
drill_canal = None
_pts = pontos_selecionados(st.session_state.get(CHAVE_DRILL))
if _pts:
    _cd = _pts[0].get("customdata")
    drill_canal = (_cd[0] if isinstance(_cd, (list, tuple)) else _cd) or _pts[0].get("y")


def recortar(d, de, ate, com_drill=True):
    m = (d["dia"] >= de) & (d["dia"] <= ate)
    if canais_sel:
        m &= d["canal"].isin(canais_sel)
    if cats_sel:
        m &= d["categoria"].isin(cats_sel)
    if pgto_sel:
        m &= d["metodo_pagamento"].isin(pgto_sel)
    if not incluir_dev:
        m &= ~d["devolvido"]
    if com_drill and drill_canal:
        m &= d["canal"] == drill_canal
    return d[m]


df = recortar(BASE, ini, fim)
df_sem_drill = recortar(BASE, ini, fim, com_drill=False)

# Período anterior de mesma duração, só quando cabe inteiro dentro da base.
dur = fim - ini + pd.Timedelta(days=1)
p_ini, p_fim = ini - dur, ini - pd.Timedelta(days=1)
comparavel = preset in ("Últimos 30 dias", "Últimos 90 dias", "Personalizado") and p_ini >= DATA_MIN
df_ant = recortar(BASE, p_ini, p_fim) if comparavel else None
dias = (fim - ini).days + 1
# Atendimento recortado só pelo período: os demais filtros não se aplicam a chamados.
atd = ATD[(ATD["dia"] >= ini) & (ATD["dia"] <= fim)] if ATD is not None else pd.DataFrame()
PED_PERIODO = int(((BASE["dia"] >= ini) & (BASE["dia"] <= fim)).sum())

if drill_canal:
    c1, c2 = st.columns([6, 1], vertical_alignment="center")
    c1.markdown(f'<span class="chip">Filtro do gráfico: canal <b>{esc(drill_canal)}</b></span>',
                unsafe_allow_html=True)
    c2.button("Limpar seleção", key="limpar_drill", width="stretch",
              on_click=lambda: st.session_state.update(versao_drill=st.session_state["versao_drill"] + 1))

if df.empty:
    st.warning("Nenhum pedido no recorte selecionado. Ajuste os filtros.")
    st.stop()

K = agregar(df).iloc[0]
KA = agregar(df_ant).iloc[0] if df_ant is not None and len(df_ant) else None
SERIE_KPI = agregar(df.assign(_p=df["dia"].dt.to_period("W" if dias <= 120 else "M").dt.start_time), "_p")


# ======================================================================
# BIG NUMBERS
# ======================================================================
def delta(chave):
    if KA is None:
        return ""
    atual, ant, info = K[chave], KA[chave], METRICAS[chave]
    if pd.isna(atual) or pd.isna(ant) or (info["tipo"] != "pct" and ant == 0):
        return ""
    if info["tipo"] == "pct":
        dif, txt = atual - ant, f"{num(abs(atual - ant))} p.p."
    else:
        dif = (atual / ant - 1) * 100
        txt = pct(abs(dif))
    if abs(dif) < 0.05:
        return '<span class="delta neutro" title="vs período anterior">estável</span>'
    classe = "bom" if (dif > 0) == (info["melhor"] > 0) else "ruim"
    seta = "▲" if dif > 0 else "▼"
    return f'<span class="delta {classe}" title="vs período anterior">{seta} {txt}</span>'


def kpi(col, rotulo, valor, sub, chave, definicao, icone):
    col.markdown(
        f'<div class="kpi" title="{esc(definicao)}"><div class="kpi-topo"><div class="kpi-rotulo">{esc(rotulo)}</div>'
        f'<div class="icone">{ICONES[icone]}</div></div><div class="kpi-valor">{valor}</div>'
        f'<div class="kpi-linha">{delta(chave)}<span>{sub}</span></div>'
        f'{sparkline(SERIE_KPI[chave].values, chave)}</div>', unsafe_allow_html=True)


k = st.columns(6, gap="small")
kpi(k[0], "Receita líquida", brl_c(K.receita), f"{brl_c(K.receita_bruta)} bruta", "receita",
    "Receita bruta menos descontos", "receita")
kpi(k[1], "Margem de contribuição", pct(K.margem_pct, 2), f"{brl_c(K.margem)}", "margem_pct",
    "Receita líquida menos CMV e frete, sobre a receita líquida", "margem")
kpi(k[2], "Margem realizada", pct(K.margem_real_pct, 2), "após devoluções", "margem_real_pct",
    "Pedido devolvido perde a receita e mantém CMV e frete (premissa do tratamento)", "realizada")
kpi(k[3], "Pedidos", inteiro(K.pedidos), f"{inteiro(K.itens)} itens", "pedidos", "Pedidos aprovados", "pedidos")
kpi(k[4], "Ticket médio", brl(K.ticket, 2), f"{num(K.itens_pedido, 2)} itens/pedido", "ticket",
    "Receita líquida por pedido", "ticket")
kpi(k[5], "Taxa de devolução", pct(K.taxa_dev), f"{inteiro(K.devolvidos)} pedidos", "taxa_dev",
    "Pedidos devolvidos sobre pedidos aprovados", "devolucao")
nota(("Variações comparadas a " + f"{p_ini:%d/%m/%Y}–{p_fim:%d/%m/%Y}, período de mesma duração. " if comparavel else "")
     + ("Minigráficos: evolução semanal no período." if dias <= 120 else "Minigráficos: evolução mensal no período."))


# ======================================================================
# INSIGHTS E RECOMENDAÇÕES (calculados sobre o recorte)
# ======================================================================
def gerar_insights(d):
    recs = []
    total = agregar(d).iloc[0]
    mk, fora = d[d["canal"] == "Marketplace"], d[d["canal"] != "Marketplace"]

    eleg = mk[mk["receita_liquida"] >= 250]
    if len(eleg) and eleg["custo_frete"].sum() > 0:
        texto = (f"{inteiro(len(eleg))} pedidos do Marketplace acima de R$ 250 pagaram "
                 f"{brl(eleg['custo_frete'].sum())} de frete.")
        alto = fora[fora["receita_liquida"] >= 250]
        if len(alto) and alto["frete_gratis"].mean() == 1:
            texto += " Nos demais canais, todos os pedidos dessa faixa têm frete grátis."
        recs.append(dict(
            tema="Frete", aba="Frete e entrega", valor=eleg["custo_frete"].sum(),
            titulo="Marketplace paga frete acima de R$ 250", texto=texto, rotulo="frete pago no período",
            acao="Negociar frete subsidiado com o marketplace acima de R$ 250 ou incorporar o frete ao preço do canal."))

    acima = d[d["desconto_pct"] > 25]
    if len(acima):
        excedente = ((acima["desconto_pct"] - 25) / 100 * acima["receita_bruta"]).sum()
        a30, d0 = d[d["desconto_pct"] >= 30], d[d["desconto_pct"] == 0]
        mesmo_volume = (len(a30) >= 30 and len(d0) >= 30
                        and abs(a30["quantidade"].mean() - d0["quantidade"].mean()) < 0.1
                        and abs(a30["receita_bruta"].mean() / d0["receita_bruta"].mean() - 1) < 0.02)
        texto = (f"{inteiro(len(acima))} pedidos ({pct(len(acima) / len(d) * 100)}) tiveram desconto acima de "
                 f"25%, somando {brl(acima['desconto_reais'].sum())} em desconto.")
        if mesmo_volume:
            texto += (" Pedidos com 30% ou mais de desconto têm a mesma quantidade de itens e o mesmo ticket "
                      "bruto dos pedidos sem desconto.")
        recs.append(dict(
            tema="Desconto", aba="Desconto", valor=excedente, rotulo="de desconto acima do teto de 25%",
            titulo="Descontos acima de 25% sem ganho de volume" if mesmo_volume else "Descontos acima de 25%",
            texto=texto, acao="Adotar teto de 25% no desconto por pedido, com aprovação obrigatória acima dele."))

    baixo = d[d["receita_liquida"] < 100]
    if len(baixo) >= 20:
        tb = agregar(baixo).iloc[0]
        if tb.margem_pct < total.margem_pct - 15:
            recs.append(dict(
                tema="Ticket", aba="Frete e entrega", valor=tb.frete, rotulo="de frete em pedidos até R$ 100",
                titulo="Pedidos até R$ 100 quase não geram margem",
                texto=(f"{inteiro(tb.pedidos)} pedidos até R$ 100 têm margem de {pct(tb.margem_pct)}, contra "
                       f"{pct(total.margem_pct)} no total. O frete consome {pct(tb.frete_pct)} da receita desses pedidos."),
                acao="Definir valor mínimo de pedido ou cobrar frete integral abaixo de R$ 100."))

    dev = d[d["devolvido"]]
    if len(dev) >= 20:
        op = dev[dev["motivo_devolucao"].isin(OPERACIONAIS)]
        custo = op["custo_produto"].sum() + op["custo_frete"].sum()
        if len(op):
            texto = (f"{pct(len(op) / len(dev) * 100, 0)} das devoluções são por defeito ou atraso na entrega "
                     f"e custaram {brl(custo)} em CMV e frete.")
            acao = "Auditar fornecedores dos produtos com mais devoluções por defeito"
            if len(mk) and len(fora):
                pm, pf = mk["tempo_entrega_real"].mean(), fora["tempo_entrega_real"].mean()
                if pm - pf >= 2:
                    texto += f" O prazo médio do Marketplace é de {num(pm)} dias, contra {num(pf)} nos demais canais."
                    acao += " e renegociar o prazo de entrega do Marketplace"
            recs.append(dict(tema="Devolução", aba="Devoluções", valor=custo, rotulo="de CMV e frete perdidos",
                             titulo="Devoluções por defeito e atraso", texto=texto, acao=acao + "."))

    meses = agregar(d, "ano_mes")
    meses = meses[meses["pedidos"] >= 100]
    if len(meses) >= 3:
        pico = meses["desconto_pct"].idxmax()
        mediana = meses.drop(pico)["desconto_pct"].median()
        excesso = meses.loc[pico, "desconto_pct"] - mediana
        if excesso >= 1:
            nome = mes_rotulo(pico, extenso=True)
            texto = (f"Em {nome} o desconto chegou a {pct(meses.loc[pico, 'desconto_pct'])} da receita bruta, "
                     f"contra mediana de {pct(mediana)} nos demais meses.")
            if meses["pedidos"].idxmax() == pico:
                texto += " Foi também o mês de maior volume de pedidos."
            recs.append(dict(
                tema="Sazonalidade", aba="Desconto", valor=excesso / 100 * meses.loc[pico, "receita_bruta"],
                rotulo="de desconto acima da mediana no mês", titulo=f"Desconto fora do padrão em {nome}",
                texto=texto,
                acao="Planejar campanhas de meses de pico com desconto limitado à mediana dos demais meses."))
    return sorted(recs, key=lambda r: -r["valor"])


RECS = gerar_insights(df)
REC = {r["tema"]: r for r in RECS}


def insight_do_tema(tema):
    r = REC.get(tema)
    if r:
        insight(r["texto"], r["acao"])


# ======================================================================
# CONTEXTO ENVIADO AO ELO AGENTS
# ----------------------------------------------------------------------
# Só indicadores já calculados sobre o recorte filtrado, com as diferenças
# prontas: o modelo é instruído a não fazer contas, e cada número que ele
# citar é conferido contra este mesmo dicionário.
# ======================================================================
def _r(v, casas=2):
    return None if v is None or pd.isna(v) else round(float(v), casas)


def _tabela(t, campos):
    return {str(i): {nome: _r(t.loc[i, col]) for nome, col in campos.items()} for i in t.index}


CAMPOS_GERAIS = {
    "pedidos": "pedidos", "receita_liquida_rs": "receita", "margem_contribuicao_rs": "margem",
    "margem_pct": "margem_pct", "margem_realizada_pct": "margem_real_pct", "ticket_medio_rs": "ticket",
    "desconto_pct_receita_bruta": "desconto_pct", "frete_pct_receita": "frete_pct", "cmv_pct_receita": "cmv_pct",
    "taxa_devolucao_pct": "taxa_dev", "prazo_medio_entrega_dias": "prazo",
}


def descricao_recorte():
    partes = [f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y}"]
    if canais_sel:
        partes.append("canais: " + ", ".join(canais_sel))
    if cats_sel:
        partes.append("categorias: " + ", ".join(cats_sel))
    if pgto_sel:
        partes.append("pagamento: " + ", ".join(pgto_sel))
    if drill_canal:
        partes.append(f"canal selecionado no gráfico: {drill_canal}")
    if not incluir_dev:
        partes.append("sem pedidos devolvidos")
    return " · ".join(partes)


def assinatura_recorte():
    return repr((str(ini.date()), str(fim.date()), tuple(canais_sel), tuple(cats_sel), tuple(pgto_sel),
                 incluir_dev, drill_canal))


DEFINICOES = {
    "margem_contribuicao": "receita líquida menos CMV e frete, sobre pedidos aprovados",
    "margem_realizada": "considera que pedidos devolvidos perdem a receita e mantêm CMV e frete",
    "desconto_pct_receita_bruta": "desconto concedido sobre a receita bruta",
    "frete_rs": "custo de frete pago pela Vértice no pedido; reduz a margem",
    "frete_gratis": ("pedido sem custo de frete para a Vértice. Nos canais fora do Marketplace, pedidos a "
                     "partir de R$ 250 não têm custo de frete. No Marketplace NÃO existe frete grátis: a "
                     "Vértice paga o frete em todos os pedidos, inclusive acima de R$ 250"),
    "valores_em_rs": "reais no período do recorte",
    "atendimento_sac": ("chamados do SAC abertos no período, pela data de abertura. Vêm de outra base e não se "
                        "ligam aos pedidos de forma confiável: os filtros de canal, categoria e pagamento não se "
                        "aplicam, e chamados não devem ser relacionados a canais de venda, categorias, produtos "
                        "ou devoluções"),
    "situacao_atual_do_estoque": ("situação do SKU na data de extração da base de estoque, não na data do pedido. "
                                  "Indica risco de reposição de itens que vendem; não explica vendas passadas"),
}


def montar_contexto():
    ctx = {
        "empresa": "Vértice Retail, e-commerce de moda, beleza, lifestyle e acessórios",
        "definicoes": DEFINICOES,
        "recorte": {"descricao": descricao_recorte(), "dias": int(dias), "pedidos": int(K.pedidos),
                    "amostra_pequena": bool(K.pedidos < 300)},
        "limiares_de_referencia": {"ticket_minimo_frete_gratis_demais_canais_rs": 250, "ticket_baixo_rs": 100,
                                   "teto_desconto_referencia_pct": 25, "desconto_alto_pct": 30},
        "totais": {**{k: _r(K[c]) for k, c in CAMPOS_GERAIS.items()},
                   "receita_bruta_rs": _r(K.receita_bruta), "desconto_rs": _r(K.desconto), "frete_rs": _r(K.frete),
                   "cmv_rs": _r(K.cmv), "itens_por_pedido": _r(K.itens_pedido),
                   "pedidos_devolvidos": int(K.devolvidos), "pedidos_margem_negativa": int(K.negativos)},
    }
    if KA is not None:
        ctx["periodo_anterior_mesma_duracao"] = {
            "descricao": f"{p_ini:%d/%m/%Y} a {p_fim:%d/%m/%Y}", **{k: _r(KA[c]) for k, c in CAMPOS_GERAIS.items()},
            "variacao_receita_pct": _r((K.receita / KA.receita - 1) * 100) if KA.receita else None,
            "variacao_pedidos_pct": _r((K.pedidos / KA.pedidos - 1) * 100) if KA.pedidos else None,
            "variacao_margem_pp": _r(K.margem_pct - KA.margem_pct),
            "variacao_desconto_pp": _r(K.desconto_pct - KA.desconto_pct),
            "variacao_taxa_devolucao_pp": _r(K.taxa_dev - KA.taxa_dev),
        }

    tc = agregar(df, "canal")
    canais = _tabela(tc, CAMPOS_GERAIS)
    for ch in canais:
        canais[ch]["participacao_receita_pct"] = _r(tc.loc[ch, "receita"] / K.receita * 100)
        canais[ch]["diferenca_margem_vs_total_pp"] = _r(tc.loc[ch, "margem_pct"] - K.margem_pct)
    ctx["por_canal"] = canais
    ctx["por_categoria"] = _tabela(agregar(df, "categoria"), CAMPOS_GERAIS)
    ctx["por_metodo_pagamento"] = _tabela(agregar(df, "metodo_pagamento"), CAMPOS_GERAIS)
    ctx["por_mes"] = _tabela(agregar(df, "mes_rotulo"), {
        "pedidos": "pedidos", "receita_liquida_rs": "receita", "margem_pct": "margem_pct",
        "desconto_pct_receita_bruta": "desconto_pct", "taxa_devolucao_pct": "taxa_dev"})
    ctx["por_faixa_ticket"] = _tabela(agregar(df, "faixa_ticket"), {
        "pedidos": "pedidos", "margem_pct": "margem_pct", "frete_pct_receita": "frete_pct", "frete_rs": "frete"})
    fxd = agregar(df, "faixa_desconto")
    fxd["margem_por_pedido"] = fxd["margem"] / fxd["pedidos"]
    fxd["ticket_bruto_medio"] = fxd["receita_bruta"] / fxd["pedidos"]
    ctx["por_faixa_desconto"] = _tabela(fxd, {
        "pedidos": "pedidos", "margem_por_pedido_rs": "margem_por_pedido", "itens_por_pedido": "itens_pedido",
        "ticket_bruto_medio_rs": "ticket_bruto_medio", "margem_pct": "margem_pct"})
    ctx["por_prazo_entrega"] = _tabela(agregar(df, "faixa_prazo"), {"pedidos": "pedidos", "taxa_devolucao_pct": "taxa_dev"})

    dev_ = df[df["devolvido"]]
    if len(dev_):
        mv = dev_.groupby("motivo_devolucao").agg(pedidos=("order_id", "count"), cmv=("custo_produto", "sum"),
                                                  frete=("custo_frete", "sum"))
        ctx["devolucoes_por_motivo"] = {
            m: {"pedidos": int(r.pedidos), "pct_das_devolucoes": _r(r.pedidos / len(dev_) * 100),
                "cmv_mais_frete_perdido_rs": _r(r.cmv + r.frete)} for m, r in mv.iterrows()}
    cc = agregar(df, ["canal", "categoria"])
    ctx["margem_pct_canal_x_categoria"] = {f"{a} | {b}": _r(cc.loc[(a, b), "margem_pct"]) for a, b in cc.index}

    mk_, fora_ = df[df["canal"] == "Marketplace"], df[df["canal"] != "Marketplace"]
    if len(mk_) and len(fora_):
        tm, tf = agregar(mk_).iloc[0], agregar(fora_).iloc[0]
        alto = fora_[fora_["receita_liquida"] >= 250]
        ctx["marketplace_vs_demais_canais"] = {
            "diferenca_margem_pp": _r(tm.margem_pct - tf.margem_pct), "diferenca_frete_pp": _r(tm.frete_pct - tf.frete_pct),
            "diferenca_prazo_dias": _r(tm.prazo - tf.prazo), "demais_canais_margem_pct": _r(tf.margem_pct),
            "demais_canais_frete_pct": _r(tf.frete_pct), "demais_canais_prazo_dias": _r(tf.prazo),
            "pct_pedidos_marketplace_com_frete_gratis": _r(mk_["frete_gratis"].mean() * 100),
            "pct_pedidos_demais_canais_a_partir_250_com_frete_gratis": _r(alto["frete_gratis"].mean() * 100) if len(alto) else None,
        }

    acima = df[df["desconto_pct"] > 25]
    oper = df[df["devolvido"] & df["motivo_devolucao"].isin(OPERACIONAIS)]
    neg = df[df["margem_negativa"]]
    d30 = df[df["desconto_pct"] > 30]
    eleg_ = df[df["mk_elegivel_nao_subsidiado"]]
    ctx["valores_calculados_rs"] = {
        "desconto_excedente_acima_de_25pct": _r(((acima["desconto_pct"] - 25) / 100 * acima["receita_bruta"]).sum()),
        "frete_marketplace_pedidos_a_partir_250": _r(eleg_["custo_frete"].sum()),
        "cmv_mais_frete_devolucoes_defeito_ou_atraso": _r(oper["custo_produto"].sum() + oper["custo_frete"].sum()),
        "frete_pedidos_ate_100": _r(df.loc[df["receita_liquida"] < 100, "custo_frete"].sum()),
    }
    ctx["alertas"] = {
        "margem_negativa": {"pedidos": int(len(neg)), "margem_total_rs": _r(neg["margem_contribuicao"].sum())},
        "desconto_acima_de_30pct": {"pedidos": int(len(d30)), "desconto_total_rs": _r(d30["desconto_reais"].sum())},
        "marketplace_pagando_frete_a_partir_250": {"pedidos": int(len(eleg_)), "frete_total_rs": _r(eleg_["custo_frete"].sum())},
        "devolucao_por_defeito_ou_atraso": {"pedidos": int(len(oper)),
                                             "cmv_mais_frete_rs": _r(oper["custo_produto"].sum() + oper["custo_frete"].sum())},
    }

    tp = agregar(df, "produto")
    tp = tp[tp["pedidos"] >= 10]
    if len(tp):
        categoria_prod = df.groupby("produto")["categoria"].first()
        ctx["produtos_menor_margem_min_10_pedidos"] = {
            p: {"categoria": categoria_prod[p], "pedidos": int(r.pedidos), "margem_pct": _r(r.margem_pct),
                "taxa_devolucao_pct": _r(r.taxa_dev)} for p, r in tp.nsmallest(10, "margem_pct").iterrows()}
        defeitos = df[df["motivo_devolucao"] == "Produto com defeito"].groupby("produto").size()
        td = pd.DataFrame({"pedidos": tp["pedidos"], "defeitos": defeitos.reindex(tp.index).fillna(0)})
        td["taxa"] = td["defeitos"] / td["pedidos"] * 100
        td = td[td["defeitos"] > 0].nlargest(10, "taxa")
        if len(td):
            ctx["produtos_mais_devolucao_por_defeito_min_10_pedidos"] = {
                p: {"categoria": categoria_prod[p], "pedidos": int(r.pedidos), "devolucoes_por_defeito": int(r.defeitos),
                    "taxa_defeito_pct": _r(r.taxa)} for p, r in td.iterrows()}

    if TEM_ESTOQUE:
        te = agregar(df, "situacao_estoque_atual")
        skus = df.groupby("situacao_estoque_atual")["sku_id"].nunique()
        ctx["por_situacao_atual_do_estoque"] = {s: {
            "skus_vendidos_no_recorte": int(skus[s]), "pedidos": int(r.pedidos), "receita_liquida_rs": _r(r.receita),
            "participacao_receita_pct": _r(r.receita / K.receita * 100)} for s, r in te.iterrows()}
        ts = agregar(df, "subcategoria")
        ts = ts[ts["pedidos"] >= 30]
        if len(ts) >= 4:
            campos_sub = {"pedidos": "pedidos", "margem_pct": "margem_pct", "desconto_pct_receita_bruta": "desconto_pct",
                          "taxa_devolucao_pct": "taxa_dev"}
            ctx["subcategorias_menor_margem_min_30_pedidos"] = _tabela(ts.nsmallest(5, "margem_pct"), campos_sub)
            ctx["subcategorias_maior_margem_min_30_pedidos"] = _tabela(ts.nlargest(5, "margem_pct"), campos_sub)
        risco = df[df["situacao_estoque_atual"].isin(["Ruptura", "Estoque Crítico"])]
        if len(risco):
            tr = risco.groupby(["sku_id", "produto", "situacao_estoque_atual"]).agg(
                pedidos=("order_id", "count"), receita=("receita_liquida", "sum")).nlargest(10, "receita")
            # Nome longo de propósito: "mais venderam hoje" fazia o modelo tratar vendas de 2023 como recentes.
            ctx["skus_de_maior_receita_no_recorte_com_estoque_atual_em_ruptura_ou_critico"] = {
                "observacao": (f"pedidos e receita de {ini:%d/%m/%Y} a {fim:%d/%m/%Y}, não são vendas recentes; "
                               "situação do estoque na data de extração"),
                "skus": [{"sku": s, "produto": p, "situacao": sit, "pedidos": int(r.pedidos),
                          "receita_liquida_rs": _r(r.receita)} for (s, p, sit), r in tr.iterrows()]}
            rt = agregar(risco).iloc[0]
            ctx["por_situacao_atual_do_estoque"]["Ruptura ou Estoque Crítico (soma)"] = {
                "skus_vendidos_no_recorte": int(risco["sku_id"].nunique()), "pedidos": int(rt.pedidos),
                "receita_liquida_rs": _r(rt.receita), "participacao_receita_pct": _r(rt.receita / K.receita * 100)}

    if len(atd):
        pc_, pm_ = tabelas_atendimento(atd)
        ctx["atendimento_sac"] = {
            "chamados": int(len(atd)), "pedidos_aprovados_no_periodo_sem_outros_filtros": PED_PERIODO,
            "chamados_por_100_pedidos": _r(len(atd) / PED_PERIODO * 100) if PED_PERIODO else None,
            "custo_total_rs": _r(atd["custo_operacional_ticket"].sum()),
            "custo_medio_por_chamado_rs": _r(atd["custo_operacional_ticket"].mean()),
            "satisfacao_media_1_a_5": _r(atd["nota_csat"].mean()),
            "pct_chamados_com_nota_1_ou_2": _r((atd["nota_csat"] <= 2).mean() * 100),
            "pendentes_na_extracao": int(atd["pendente"].sum()),
            "por_canal_de_entrada": _tabela(pc_, {
                "chamados": "chamados", "participacao_chamados_pct": "part_chamados", "custo_rs": "custo",
                "participacao_custo_pct": "part_custo", "custo_por_chamado_rs": "custo_chamado",
                "satisfacao_media": "csat", "primeira_resposta_mediana_min": "resposta_min", "pendentes": "pendentes"}),
            "por_motivo": _tabela(pm_, {"chamados": "chamados", "participacao_chamados_pct": "part_chamados",
                                        "satisfacao_media": "csat", "pendentes": "pendentes"}),
        }

    ctx["sinais_detectados_por_regras"] = [{"tema": r["tema"], "titulo": r["titulo"], "valor_rs": _r(r["valor"])}
                                           for r in RECS]
    return ctx


# ======================================================================
# CARTÕES DE RECOMENDAÇÃO (regras e Elo Agents)
# ======================================================================
def _rec_html(i, tema, titulo, texto, acao, topo_direita, valor_html="", rodape=""):
    cor = TEMA_COR.get(tema, VIOLETA)
    return (f'<div class="rec"><div class="rec-topo"><span class="rank">{i:02d}</span>'
            f'<span class="tema" style="background:{cor}33;border:1px solid {cor}80">{esc(tema)}</span>'
            f'<span class="rec-aba">{topo_direita}</span></div>'
            f'<div class="rec-titulo">{esc(titulo)}</div><div class="rec-texto">{esc(texto)}</div>'
            f'{valor_html}<div class="rec-acao"><b>Ação:</b> {esc(acao)}</div>{rodape}</div>')


def _valor_html(valor, rotulo, maior, fonte=""):
    if valor is None:
        return ""
    largura = max(4, abs(valor) / maior * 100) if maior else 4
    return (f'<div class="rec-valor" title="{esc(fonte)}"><b>{brl_c(valor)}</b>{esc(rotulo)}</div>'
            f'<div class="medidor"><span style="width:{largura:.0f}%"></span></div>')


def render_recs_regras():
    if not RECS:
        nota("Nenhum ponto de atenção com amostra suficiente neste recorte.")
        return
    maior = max(r["valor"] for r in RECS)
    st.markdown('<div class="recs">' + "".join(
        _rec_html(i, r["tema"], r["titulo"], r["texto"], r["acao"], f'Aba {esc(r["aba"])}',
                  _valor_html(r["valor"], r["rotulo"], maior))
        for i, r in enumerate(RECS, start=1)) + "</div>", unsafe_allow_html=True)


def _selo_conferencia(faltam):
    if not faltam:
        return '<div class="selo ok">Números conferidos com os dados enviados</div>'
    return (f'<div class="selo alerta" title="Esses valores não aparecem nos indicadores enviados ao Elo Agents">'
            f'Confira: {esc(", ".join(faltam[:4]))} fora dos dados enviados</div>')


def aviso(titulo, texto, erro=False):
    st.markdown(f'<div class="aviso{" erro" if erro else ""}"><b>{esc(titulo)}</b><div>{esc(texto)}</div></div>',
                unsafe_allow_html=True)


def render_insights_ia(ia, desatualizado):
    res = ia["resultado"]
    meta = (f'Gerado em {ia["quando"]:%d/%m às %H:%M} · {esc(res["modelo"])} · {num(res["segundos"], 1)} s · '
            f'recorte {esc(ia["recorte"])}')
    if ia["pergunta"]:
        meta += f' · pergunta: {esc(ia["pergunta"])}'
    selo = ('<span class="selo alerta">Os dados mudaram depois desta análise; gere de novo para atualizar</span>'
            if desatualizado else "")
    st.markdown(f'<div class="ia-meta">{selo}<span>{meta}</span></div>', unsafe_allow_html=True)
    if res["resumo"]:
        insight(res["resumo"], rotulo="Resumo do Elo Agents")
        if res["resumo_nao_conferidos"]:
            st.markdown(_selo_conferencia(res["resumo_nao_conferidos"]), unsafe_allow_html=True)
    valores = [abs(x["valor"]) for x in res["insights"] if x["valor"] is not None]
    maior = max(valores) if valores else 0
    st.markdown('<div class="recs">' + "".join(
        _rec_html(i, x["tema"], x["titulo"], x["texto"], x["acao"], f'Prioridade {esc(x["prioridade"])}',
                  # valor em jogo que não existe nos dados enviados não ganha destaque; o selo continua avisando
                  _valor_html(None if "valor em jogo" in x["nao_conferidos"] else x["valor"], "valor em jogo", maior,
                              fonte=f'Fonte: {x["base_valor"]}'),
                  _selo_conferencia(x["nao_conferidos"]))
        for i, x in enumerate(res["insights"], start=1)) + "</div>", unsafe_allow_html=True)
    nota("A conferência verifica os números citados, não a interpretação. Ações e hipóteses são sugestões do modelo: "
         "revise antes de decidir.")
    c = st.columns(2, gap="small")
    with c[0].expander("Dados enviados ao Elo Agents"):
        st.json(ia["contexto"], expanded=False)
    with c[1].expander("Resposta original do modelo"):
        st.code(res["bruto"], language="json")


abas = st.tabs(["Visão geral", "Explorar", "Canais", "Desconto", "Frete e entrega", "Devoluções",
                "Atendimento", "Alertas", "Simulador"])

# ======================================================================
# VISÃO GERAL
# ======================================================================
with abas[0]:
    with card("evolucao"):
        cabecalho("Evolução no período", "Escolha a métrica e a granularidade")
        opcoes_evo = {"Receita líquida": "receita", "Margem (%)": "margem_pct", "Pedidos": "pedidos",
                      "Ticket médio": "ticket", "Desconto (%)": "desconto_pct", "Devolução (%)": "taxa_dev"}
        g = st.columns([3, 1.2], vertical_alignment="center")
        met_evo = opcoes_evo[g[0].segmented_control("Métrica", list(opcoes_evo), default="Receita líquida",
                                                    required=True, key="evo_metrica", label_visibility="collapsed")]
        gran = g[1].segmented_control("Granularidade", ["Dia", "Semana", "Mês"],
                                      default="Dia" if dias <= 45 else ("Semana" if dias <= 180 else "Mês"),
                                      required=True, key=f"evo_gran_{preset}", label_visibility="collapsed")
        freq = {"Dia": "D", "Semana": "W", "Mês": "M"}[gran]
        serie = agregar(df.assign(periodo=df["dia"].dt.to_period(freq).dt.start_time), "periodo")
        info = METRICAS[met_evo]
        rotulo_x = ([mes_rotulo(p.strftime("%Y-%m")) for p in serie.index] if gran == "Mês"
                    else [p.strftime("%d/%m/%y") for p in serie.index])
        aditiva = met_evo in ADITIVAS
        fig = go.Figure(go.Scatter(
            x=rotulo_x, y=serie[met_evo], mode="lines+markers" if len(serie) <= 40 else "lines",
            line=dict(color=VIOLETA, width=2.5),
            marker=dict(size=8, color=VIOLETA, line=dict(color=ROXO_ESCURO, width=2)),
            fill="tozeroy" if aditiva else None,
            fillgradient=dict(type="vertical", colorscale=[[0, "rgba(139,92,246,0)"], [1, "rgba(139,92,246,0.45)"]])
            if aditiva else None,
            hovertemplate=hover_num(info["tipo"], "y") + "<extra></extra>", name=info["nome"]))
        pico_i = int(np.nanargmax(serie[met_evo].values))
        fig.add_scatter(x=[rotulo_x[pico_i]], y=[serie[met_evo].iloc[pico_i]], mode="markers+text",
                        marker=dict(size=11, color=ROSA, line=dict(color=ROXO_ESCURO, width=2)),
                        text=[f"Máximo: {fmt(serie[met_evo].iloc[pico_i], info['tipo'])}"], textposition="top center",
                        textfont=dict(size=11, color=TEXTO), hoverinfo="skip", showlegend=False)
        fig.update_layout(hovermode="x unified")
        fig.update_xaxes(showspikes=True, spikemode="across", spikethickness=1, spikecolor=BORDA_FORTE,
                         spikedash="solid", nticks=14)
        fig.update_yaxes(**eixo_fmt(info["tipo"]), rangemode="tozero" if aditiva else "normal")
        topo_y = np.nanmax(serie[met_evo].values)
        if aditiva:
            fig.update_yaxes(range=[0, topo_y * 1.18])
        plot(estilo(fig, H_M))
        nota("Semanas e meses nas pontas do período podem estar incompletos.")

    c = st.columns(2, gap="small")
    with c[0]:
        with card("margem_canal"):
            cabecalho("Margem por canal", "Clique numa barra para filtrar o painel pelo canal")
            t = agregar(df_sem_drill, "canal")
            foco = {drill_canal} if drill_canal else {t["margem_pct"].idxmin()}
            ordem_t = t.sort_values("margem_pct")
            fig = barras_h(t, "margem_pct", "pct", foco=foco, altura=H_M,
                           customdata=[[i, brl_c(r)] for i, r in zip(ordem_t.index, ordem_t["receita"])])
            fig.update_traces(hovertemplate="<b>%{y}</b><br>Margem: %{x:.1f}%<br>Receita: %{customdata[1]}<extra></extra>",
                              unselected=dict(marker=dict(opacity=1)))
            plot(fig, key=CHAVE_DRILL, selecionavel=True)
            if "Marketplace" in t.index and len(t) > 1:
                demais = agregar(df_sem_drill[df_sem_drill["canal"] != "Marketplace"]).iloc[0]
                gap = demais.margem_pct - t.loc["Marketplace", "margem_pct"]
                gap_frete = t.loc["Marketplace", "frete_pct"] - demais.frete_pct
                if gap > 0:
                    insight(f"O Marketplace tem margem {num(gap)} p.p. abaixo dos demais canais somados. "
                            f"O frete, sozinho, pesa {num(gap_frete)} p.p. a mais na receita do Marketplace.")
    with c[1]:
        with card("ponte"):
            cabecalho("Composição da margem", "Da receita bruta à margem de contribuição")
            fig = go.Figure(go.Waterfall(
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["Receita bruta", "Desconto", "CMV", "Frete", "Margem"],
                y=[K.receita_bruta, -K.desconto, -K.cmv, -K.frete, K.margem],
                text=[brl_c(K.receita_bruta), brl_c(-K.desconto), brl_c(-K.cmv), brl_c(-K.frete), brl_c(K.margem)],
                textposition="outside", textfont=dict(size=11, color=TEXTO_2),
                connector=dict(line=dict(color=BORDA_FORTE, width=1)),
                decreasing=dict(marker=dict(color=ROSA)), increasing=dict(marker=dict(color=VIOLETA)),
                totals=dict(marker=dict(color=VIOLETA)), hovertemplate="%{x}: %{text}<extra></extra>"))
            fig.update_yaxes(range=[0, K.receita_bruta * 1.15], tickprefix="R$ ", tickformat="~s")
            plot(estilo(fig, H_M))
            insight(f"Desconto e frete somam {brl_c(K.desconto + K.frete)}, "
                    f"{pct((K.desconto + K.frete) / K.receita_bruta * 100)} da receita bruta. São as deduções "
                    f"que dependem de decisão comercial; o CMV representa {pct(K.cmv_pct)} da receita líquida.")

    with card("recs"):
        cabecalho("Insights e ações recomendadas",
                  "Gerados sob demanda pelo Elo Agents a partir dos indicadores do recorte filtrado. Cada número "
                  "citado é conferido com os dados enviados.")
        assinatura = assinatura_recorte()
        if not elo_agents.configurado():
            aviso("Elo Agents não configurado",
                  'Crie o arquivo .streamlit/secrets.toml com a linha ELOAGENTS_API_KEY = "sua-chave" (no deploy, '
                  "cadastre o mesmo nome em Secrets) e recarregue a página. Enquanto isso, seguem os sinais "
                  "calculados por regras, sem IA.")
            st.markdown('<div class="subtitulo-recs">Sinais calculados por regras (sem IA)</div>', unsafe_allow_html=True)
            render_recs_regras()
        else:
            c = st.columns([4, 1.1, 1.2], gap="small", vertical_alignment="bottom")
            pergunta = c[0].text_input("Pergunta ou foco da análise (opcional)", key="ia_pergunta",
                                       placeholder="Ex.: o que priorizar no Marketplace nas próximas semanas?")
            with c[1].popover("Modelo", width="stretch"):
                opcoes = st.session_state.get("ia_modelos") or [elo_agents.modelo_padrao()]
                st.selectbox("Modelo do Elo Agents", opcoes, key="ia_modelo")
                if st.button("Buscar modelos disponíveis", key="ia_listar", width="stretch"):
                    try:
                        st.session_state["ia_modelos"] = elo_agents.listar_modelos() or opcoes
                        st.rerun()
                    except elo_agents.ErroElo as e:
                        nota(e.mensagem)
            gerar = c[2].button("Gerar insights", type="primary", width="stretch", key="ia_gerar")

            if gerar:
                contexto = montar_contexto()
                modelo = st.session_state.get("ia_modelo") or elo_agents.modelo_padrao()
                with st.spinner("Consultando o Elo Agents com os indicadores do recorte. A análise leva cerca de 30 segundos..."):
                    try:
                        resultado = elo_agents.gerar_insights(contexto, pergunta.strip() or None, modelo)
                        st.session_state["ia"] = dict(
                            assinatura=assinatura, recorte=descricao_recorte(), pergunta=pergunta.strip(),
                            resultado=resultado, contexto=contexto, quando=pd.Timestamp.now(tz="America/Sao_Paulo"))
                        st.session_state.pop("ia_erro", None)
                    except elo_agents.ErroElo as e:
                        st.session_state["ia_erro"] = dict(tipo=e.tipo, mensagem=e.mensagem, bruto=e.bruto)

            erro = st.session_state.get("ia_erro")
            if erro:
                aviso("Não foi possível gerar os insights", erro["mensagem"], erro=True)
                if erro.get("bruto"):
                    with st.expander("Detalhe técnico"):
                        st.code(str(erro["bruto"])[:4000])
            ia = st.session_state.get("ia")
            if ia:
                render_insights_ia(ia, desatualizado=ia["assinatura"] != assinatura)
            elif not erro:
                nota("Clique em Gerar insights para o Elo Agents analisar o recorte atual. Os indicadores enviados "
                     "ficam visíveis depois da análise, em 'Dados enviados ao Elo Agents'.")
            with st.expander("Sinais calculados por regras (sem IA)"):
                render_recs_regras()

# ======================================================================
# EXPLORAR (self-service)
# ======================================================================
DIMENSOES = {"Canal": "canal", "Categoria": "categoria",
             **({"Subcategoria": "subcategoria"} if TEM_ESTOQUE else {}),
             "Método de pagamento": "metodo_pagamento",
             "Faixa de ticket": "faixa_ticket", "Faixa de desconto": "faixa_desconto",
             "Prazo de entrega": "faixa_prazo", "Mês": "mes_rotulo", "Motivo de devolução": "motivo_devolucao",
             "Produto": "produto",
             **({"Situação atual do estoque": "situacao_estoque_atual"} if TEM_ESTOQUE else {})}
LIMITADAS = {"produto", "subcategoria"}  # muitas linhas: exibem só os 15 maiores ou menores
ORDENADAS = {"faixa_ticket", "faixa_desconto", "faixa_prazo", "mes_rotulo"}
QUEBRAS = {"Canal": "canal", "Categoria": "categoria", "Método de pagamento": "metodo_pagamento"}
COLS_PEDIDO = {"order_id": "Pedido", "data_pedido": "Data", "canal": "Canal", "categoria": "Categoria",
               "produto": "Produto", "metodo_pagamento": "Pagamento", "receita_liquida": "Receita líquida (R$)",
               "desconto_pct": "Desconto (%)", "custo_frete": "Frete (R$)", "margem_contribuicao": "Margem (R$)",
               "margem_pct": "Margem (%)", "tempo_entrega_real": "Prazo (dias)", "motivo_devolucao": "Devolução"}


def tabela_pedidos(d, chave, altura=380):
    t = d[list(COLS_PEDIDO)].rename(columns=COLS_PEDIDO).sort_values("Margem (R$)")
    cfg = {c: st.column_config.NumberColumn(c, format="localized") for c in t.columns
           if t[c].dtype.kind in "fi"}
    cfg["Data"] = st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY")
    st.dataframe(t, hide_index=True, height=altura, column_config=cfg, key=f"tab_{chave}")
    st.download_button("Exportar CSV", csv_bytes(t), file_name=f"pedidos_{chave}.csv", mime="text/csv",
                       key=f"csv_{chave}")


with abas[1]:
    with card("explorar"):
        cabecalho("Explorar dados", "Escolha dimensão, métrica e quebra. Clique em barras ou células para listar os pedidos.")
        c = st.columns([1.1, 1.4, 1.1, 1.2], gap="small", vertical_alignment="bottom")
        dim_nome = c[0].selectbox("Dimensão", list(DIMENSOES), key="exp_dim")
        dim = DIMENSOES[dim_nome]
        met = {v["nome"]: k for k, v in METRICAS.items()}[
            c[1].selectbox("Métrica", [v["nome"] for v in METRICAS.values()], index=2, key="exp_met")]
        quebra_nome = c[2].selectbox("Quebrar por", ["Nenhuma"] + [q for q in QUEBRAS if QUEBRAS[q] != dim],
                                     key="exp_quebra")
        quebra = QUEBRAS.get(quebra_nome)
        base_exp = df[df["devolvido"]] if dim == "motivo_devolucao" else df
        if dim in LIMITADAS:
            lado = c[3].segmented_control("Exibir", ["15 maiores", "15 menores"], default="15 maiores",
                                          required=True, key="exp_lado")
        info = METRICAS[met]

        t = agregar(base_exp, dim)
        if dim in LIMITADAS:
            t = t[t["pedidos"] >= 10].sort_values(met, ascending=lado == "15 menores").head(15)
        membros = list(t.index)
        altura_exp = max(H_M, 30 * len(membros) + 70) if dim not in ORDENADAS else H_G
        chave_exp = f"exp_{dim}_{met}_{quebra}"

        if quebra is None:
            if dim in ORDENADAS:
                fig = colunas([str(i) for i in t.index], t[met].values, info["tipo"], altura=altura_exp,
                              rotulos=len(t) <= 14)
                fig.update_traces(customdata=[str(i) for i in t.index],
                                  hovertemplate="<b>%{x}</b><br>" + hover_num(info["tipo"], "y") + "<extra></extra>")
            else:
                fig = barras_h(t, met, info["tipo"], altura=altura_exp)
        elif met in ADITIVAS:
            tq = agregar(base_exp[base_exp[dim].isin(membros)], [dim, quebra])[met].unstack(quebra).reindex(membros)
            if dim not in ORDENADAS:
                tq = tq.loc[t[met].sort_values().index]
            fig = go.Figure()
            for q in [q for q in CORES_DIM[quebra] if q in tq.columns]:
                eixo_cat = [str(i) for i in tq.index]
                kw = dict(x=eixo_cat, y=tq[q]) if dim in ORDENADAS else dict(y=eixo_cat, x=tq[q], orientation="h")
                fig.add_bar(**kw, name=q, marker_color=CORES_DIM[quebra][q],
                            marker_line=dict(color=ROXO_ESCURO, width=1.5),
                            customdata=[[i, q] for i in eixo_cat],
                            hovertemplate=f"<b>%{{{'x' if dim in ORDENADAS else 'y'}}}</b> · {esc(q)}<br>"
                            + hover_num(info["tipo"], "y" if dim in ORDENADAS else "x") + "<extra></extra>")
            fig.update_layout(barmode="stack")
            (fig.update_yaxes if dim in ORDENADAS else fig.update_xaxes)(**eixo_fmt(info["tipo"]))
            fig = estilo(fig, altura_exp, horizontal=dim not in ORDENADAS, legenda=True)
        else:
            tq = agregar(base_exp[base_exp[dim].isin(membros)], [dim, quebra])[met].unstack(quebra).reindex(membros)
            tq = tq[[q for q in CORES_DIM[quebra] if q in tq.columns]]
            texto_cel = {"pct": "%{z:.1f}%", "brl": "R$ %{z:,.0f}", "brl2": "R$ %{z:,.2f}", "int": "%{z:,.0f}",
                         "dec": "%{z:.2f}"}[info["tipo"]]
            fig = go.Figure(go.Heatmap(
                z=tq.values, x=list(tq.columns), y=[str(i) for i in tq.index], colorscale=ESCALA_SEQ,
                xgap=3, ygap=3,
                hovertemplate="<b>%{y}</b> · %{x}<br>" + texto_cel + "<extra></extra>",
                colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(size=11, color=TEXTO_3))))
            rotular_celulas(fig, tq.values, list(tq.columns), [str(i) for i in tq.index],
                            lambda v: fmt(v, info["tipo"]))
            fig.update_yaxes(autorange="reversed")
            fig = estilo(fig, max(H_M, 36 * len(tq) + 60))
            fig.update_yaxes(tickfont=dict(size=12, color=TEXTO_2), showgrid=False)
        evento = plot(fig, key=chave_exp, selecionavel=True)
        if dim in LIMITADAS:
            nota(f"Somente {dim_nome.lower()}s com pelo menos 10 pedidos no recorte, para evitar conclusões sobre "
                 "amostras pequenas.")
        if dim == "situacao_estoque_atual":
            nota("Situação do SKU na extração da base de estoque, não na data do pedido: mostra quanto do que "
                 "vendeu está hoje em ruptura, crítico ou descontinuado.")
        if dim == "motivo_devolucao":
            nota("Considera apenas pedidos devolvidos.")

        filtros_sel = []
        for p in pontos_selecionados(evento):
            cd = p.get("customdata")
            if isinstance(cd, (list, tuple)) and len(cd) == 2:
                filtros_sel.append((cd[0], cd[1]))
            elif cd is not None:
                filtros_sel.append((cd[0] if isinstance(cd, (list, tuple)) else cd, None))
            elif p.get("y") is not None and p.get("x") is not None and quebra and met not in ADITIVAS:
                filtros_sel.append((p["y"], p["x"]))

    c = st.columns([1.6, 1], gap="small")
    with c[0]:
        with card("exp_tabela"):
            cabecalho(f"Tabela por {dim_nome.lower()}", "Todas as métricas para os itens exibidos no gráfico")
            vis = t.copy()
            vis.index = vis.index.astype(str)
            # a métrica escolhida vem logo depois da dimensão, mesmo quando não está entre as colunas padrão
            colunas_padrao = ["pedidos", "receita", "margem", "margem_pct", "margem_real_pct", "ticket",
                              "desconto_pct", "desconto", "frete_pct", "frete", "taxa_dev", "prazo"]
            vis = vis[[met] + [c for c in colunas_padrao if c != met]].rename(
                columns={k2: METRICAS[k2]["nome"] for k2 in METRICAS})
            vis = vis.reset_index().rename(columns={dim: dim_nome})
            st.dataframe(vis, hide_index=True, height=min(420, 38 * len(vis) + 40),
                         column_config={col: st.column_config.NumberColumn(col, format="localized")
                                        for col in vis.columns if col != dim_nome}, key="exp_df")
            st.download_button("Exportar CSV", csv_bytes(vis), file_name=f"resumo_{dim}.csv", mime="text/csv",
                               key="exp_csv")
    with c[1]:
        with card("exp_detalhe"):
            if filtros_sel:
                m = pd.Series(False, index=base_exp.index)
                for membro, q in filtros_sel:
                    cond = base_exp[dim].astype(str) == str(membro)
                    if q is not None and quebra:
                        cond &= base_exp[quebra] == q
                    m |= cond
                sel = base_exp[m]
                rotulo_sel = ", ".join(sorted({f"{a} · {b}" if b else str(a) for a, b in filtros_sel}))
                cabecalho("Pedidos da seleção", f"{rotulo_sel}: {inteiro(len(sel))} pedidos, margem de "
                          f"{pct(agregar(sel).iloc[0].margem_pct)}")
                tabela_pedidos(sel, "selecao", altura=330)
            else:
                cabecalho("Pedidos da seleção", "Clique numa barra ou célula do gráfico acima para listar os pedidos.")

    def contexto_tabela():
        """Só o que está na tela da aba Explorar: configuração, tabela resumo, matriz do gráfico
        (quando há quebra) e a seleção de pedidos (quando há)."""
        linhas = vis.copy()
        for col in linhas.columns:
            if linhas[col].dtype.kind in "fi":
                linhas[col] = linhas[col].map(_r)
        observacoes = []
        if dim in LIMITADAS:
            observacoes.append(f"somente {dim_nome.lower()}s com pelo menos 10 pedidos; exibidos os {lado}")
        if dim == "situacao_estoque_atual":
            observacoes.append(DEFINICOES["situacao_atual_do_estoque"])
        if dim == "motivo_devolucao":
            observacoes.append("considera apenas pedidos devolvidos")
        # Só as definições que a métrica escolhida precisa: a definição longa de frete, enviada
        # sempre, puxava os insights de qualquer tabela para frete.
        chaves_definicao = ["margem_contribuicao", "margem_realizada", "valores_em_rs"]
        if met in ("frete", "frete_pct"):
            chaves_definicao += ["frete_rs", "frete_gratis"]
        if met in ("desconto", "desconto_pct"):
            chaves_definicao.append("desconto_pct_receita_bruta")
        coluna_foco = info["nome"]
        registros = linhas.to_dict(orient="records")
        ranking = sorted(((str(r_[dim_nome]), r_[coluna_foco]) for r_ in registros if r_[coluna_foco] is not None),
                         key=lambda par: -par[1])
        # Comparações já calculadas, para o modelo citar em vez de fazer contas (e para a conferência).
        # O total vem da mesma base da tabela: em "Motivo de devolução", só os pedidos devolvidos.
        total_foco = _r(agregar(base_exp).iloc[0][met])
        chave_dif = "diferenca_vs_total_pp" if info["tipo"] == "pct" else "diferenca_vs_total"
        ranking_ctx = []
        for nome, valor in ranking:
            item = {dim_nome: nome, coluna_foco: valor}
            if met in ADITIVAS and total_foco:
                item["participacao_no_total_pct"] = _r(valor / total_foco * 100)
            elif met not in ADITIVAS and total_foco is not None:
                item[chave_dif] = _r(valor - total_foco)
            ranking_ctx.append(item)
        resumo_foco = ({"total_da_base": total_foco, "maior": ranking[0][1], "linha_do_maior": ranking[0][0],
                        "menor": ranking[-1][1], "linha_do_menor": ranking[-1][0],
                        "amplitude": _r(ranking[0][1] - ranking[-1][1])} if ranking else {})
        ctx = {
            "painel": "Aba Explorar dados do painel de rentabilidade da Vértice Retail",
            "definicoes": {k: DEFINICOES[k] for k in chaves_definicao},
            "recorte": {"descricao": descricao_recorte(), "pedidos": int(K.pedidos)},
            "configuracao": {"dimensao": dim_nome, "metrica_foco": coluna_foco, "quebra": quebra_nome,
                             "maior_valor_e_melhor": {1: "sim", -1: "não", 0: "neutro"}[info["melhor"]],
                             "observacoes": observacoes},
            "totais_do_recorte": {**{k: _r(K[c]) for k, c in CAMPOS_GERAIS.items()},
                                  "metrica_foco_total": _r(K[met])},
            "resumo_da_metrica_foco": resumo_foco,
            "ranking_da_metrica_foco": ranking_ctx,
            "tabela_resumo": registros,
        }
        if quebra:
            mat = agregar(base_exp[base_exp[dim].isin(membros)], [dim, quebra])[met].unstack(quebra)
            ctx["matriz_do_grafico"] = {
                "metrica": info["nome"], "linhas": dim_nome, "colunas": quebra_nome,
                "valores": {str(i): {str(q): _r(mat.loc[i, q]) for q in mat.columns} for i in mat.index}}
            celulas = [(str(i), str(q), _r(mat.loc[i, q])) for i in mat.index for q in mat.columns
                       if pd.notna(mat.loc[i, q])]
            if celulas:
                alta, baixa = max(celulas, key=lambda c_: c_[2]), min(celulas, key=lambda c_: c_[2])
                ctx["matriz_do_grafico"]["resumo"] = {
                    "maior_celula": {"linha": alta[0], "coluna": alta[1], "valor": alta[2]},
                    "menor_celula": {"linha": baixa[0], "coluna": baixa[1], "valor": baixa[2]}}
        if filtros_sel:
            ks = agregar(sel).iloc[0]
            campos_pedido = {"produto": "produto", "canal": "canal", "categoria": "categoria",
                             "metodo_pagamento": "pagamento", "receita_liquida": "receita_liquida_rs",
                             "desconto_pct": "desconto_pct", "custo_frete": "frete_rs",
                             "margem_contribuicao": "margem_rs", "margem_pct": "margem_pct",
                             "tempo_entrega_real": "prazo_dias", "motivo_devolucao": "devolucao"}
            amostra = sel.sort_values("margem_contribuicao").head(40)
            ctx["tabela_pedidos_da_selecao"] = {
                "selecao": rotulo_sel, "pedidos": int(len(sel)),
                "resumo_da_selecao": {k: _r(ks[c]) for k, c in CAMPOS_GERAIS.items()},
                "criterio_das_linhas": f"os {len(amostra)} pedidos com menor margem, na ordem da tabela",
                "linhas": [{novo: (_r(linha[orig]) if isinstance(linha[orig], (int, float, np.number)) else str(linha[orig]))
                            for orig, novo in campos_pedido.items()} for _, linha in amostra.iterrows()],
            }
        return ctx

    with card("exp_ia"):
        topo = st.columns([4, 1.3], gap="small", vertical_alignment="center")
        with topo[0]:
            cabecalho("Insights sobre as tabelas",
                      "O Elo Agents analisa só os dados das tabelas acima, na configuração atual de dimensão, "
                      "métrica, quebra e seleção.")
        assinatura_tab = assinatura_recorte() + repr((dim, met, quebra, lado if dim in LIMITADAS else None,
                                                      sorted(map(str, filtros_sel))))
        if not elo_agents.configurado():
            aviso("Elo Agents não configurado",
                  'Defina ELOAGENTS_API_KEY em .streamlit/secrets.toml para gerar insights sobre as tabelas.')
        else:
            if topo[1].button("Gerar insights da tabela", type="primary", width="stretch", key="ia_tab_gerar"):
                ctx_tab = contexto_tabela()
                descricao_tab = (f"tabela por {dim_nome.lower()} · {info['nome']}"
                                 + (f" · quebra por {quebra_nome.lower()}" if quebra else "")
                                 + (f" · seleção: {rotulo_sel}" if filtros_sel else "")
                                 + f" · {descricao_recorte()}")
                with st.spinner("Consultando o Elo Agents com os dados das tabelas. A análise leva cerca de 30 segundos..."):
                    try:
                        resultado_tab = elo_agents.gerar_insights_tabela(
                            ctx_tab, st.session_state.get("ia_modelo") or elo_agents.modelo_padrao())
                        st.session_state["ia_tab"] = dict(
                            assinatura=assinatura_tab, recorte=descricao_tab, pergunta="", resultado=resultado_tab,
                            contexto=ctx_tab, quando=pd.Timestamp.now(tz="America/Sao_Paulo"))
                        st.session_state.pop("ia_tab_erro", None)
                    except elo_agents.ErroElo as e:
                        st.session_state["ia_tab_erro"] = dict(tipo=e.tipo, mensagem=e.mensagem, bruto=e.bruto)
            erro_tab = st.session_state.get("ia_tab_erro")
            if erro_tab:
                aviso("Não foi possível gerar os insights da tabela", erro_tab["mensagem"], erro=True)
            ia_tab = st.session_state.get("ia_tab")
            if ia_tab:
                render_insights_ia(ia_tab, desatualizado=ia_tab["assinatura"] != assinatura_tab)
            elif not erro_tab:
                nota("Clique em Gerar insights da tabela. A análise usa exatamente o que está nas tabelas acima e "
                     "muda conforme a dimensão, a métrica, a quebra e a seleção escolhidas.")

# ======================================================================
# CANAIS
# ======================================================================
with abas[2]:
    tc = agregar(df, "canal")
    c = st.columns([1.35, 1], gap="small")
    with c[0]:
        with card("custos_canal"):
            cabecalho("Custos por canal", "CMV e frete em % da receita líquida; desconto em % da receita bruta")
            ordem = tc.sort_values("frete_pct").index
            fig = make_subplots(rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.05,
                                subplot_titles=("CMV", "Frete", "Desconto"))
            for i, col in enumerate(["cmv_pct", "frete_pct", "desconto_pct"], start=1):
                fig.add_bar(y=list(ordem), x=tc.loc[ordem, col], orientation="h", row=1, col=i, showlegend=False,
                            marker_color=[COR_FOCO if ch == "Marketplace" else COR_BASE for ch in ordem],
                            text=[pct(v) for v in tc.loc[ordem, col]], textposition="outside",
                            textfont=dict(size=11, color=TEXTO_2),
                            hovertemplate="<b>%{y}</b><br>%{x:.2f}%<extra></extra>")
                fig.update_xaxes(range=[0, tc[col].max() * 1.45], showticklabels=False, row=1, col=i)
            estilo(fig, H_M + 40, horizontal=True)
            fig.update_xaxes(showgrid=False)
            fig.update_annotations(font=dict(size=12, color=TEXTO_2))
            fig.update_layout(margin=dict(t=28))
            plot(fig)
            if len(tc) > 1:
                amp = tc.max() - tc.min()
                insight(f"Entre os canais, o CMV varia {num(amp['cmv_pct'])} p.p. e o desconto {num(amp['desconto_pct'])} p.p. "
                        f"O frete vai de {pct(tc['frete_pct'].min())} a {pct(tc['frete_pct'].max())} da receita, "
                        f"com o maior peso em {tc['frete_pct'].idxmax()}.")
    with c[1]:
        with card("mapa_canais"):
            cabecalho("Receita e margem por canal e categoria",
                      "Área = receita líquida. Cor = margem: rosa abaixo da média do recorte, ciano acima. "
                      "Clique num canal para abrir as categorias.")
            tcc = agregar(df, ["canal", "categoria"])
            media = K.margem_pct
            # Raiz explícita e valores de cada pai somados dos filhos: com branchvalues="total", um pai
            # menor que a soma dos filhos (arredondamento) faz o Plotly não desenhar o bloco.
            ids, rotulos, pais, valores, margens, extra = ["Todos"], ["Todos os canais"], [""], [0.0], [np.nan], [None]
            for ch in [x for x in COR_CANAL if x in tc.index]:
                cats = [x for x in COR_CATEGORIA if (ch, x) in tcc.index]
                soma_ch = float(sum(tcc.loc[(ch, cat), "receita"] for cat in cats))
                ids.append(ch)
                rotulos.append(ch)
                pais.append("Todos")
                valores.append(soma_ch)
                margens.append(tc.loc[ch, "margem_pct"])
                extra.append([brl_c(soma_ch), pct(tc.loc[ch, "margem_pct"])])
                valores[0] += soma_ch
                for cat in cats:
                    linha = tcc.loc[(ch, cat)]
                    ids.append(f"{ch} / {cat}")
                    rotulos.append(cat)
                    pais.append(ch)
                    valores.append(float(linha["receita"]))
                    margens.append(linha["margem_pct"])
                    extra.append([brl_c(linha["receita"]), pct(linha["margem_pct"])])
            extra[0] = [brl_c(valores[0]), pct(media)]
            desvio = max(float(np.nanmax(np.abs(np.array(margens[1:], dtype=float) - media))), 0.5)
            # Cores calculadas aqui, não pela escala do Plotly: com escala contínua ele ignora a cor da
            # raiz e pinta um retângulo cinza atrás de todos os blocos.
            posicoes = [min(max((m - media) / (2 * desvio) + 0.5, 0.0), 1.0) for m in margens[1:]]
            cores = ["rgba(0,0,0,0)"] + sample_colorscale(ESCALA_DIV, posicoes)
            fig = go.Figure(go.Treemap(
                ids=ids, labels=rotulos, parents=pais, values=valores, branchvalues="total", customdata=extra,
                marker=dict(colors=cores, line=dict(color=ROXO_ESCURO, width=2), cornerradius=6),
                texttemplate="<b>%{label}</b><br>%{customdata[0]}<br>%{customdata[1]}",
                textfont=dict(size=12, color="#FFFFFF"),
                hovertemplate="<b>%{label}</b><br>Receita: %{customdata[0]}<br>Margem: %{customdata[1]}<extra></extra>",
                pathbar=dict(visible=True, textfont=dict(color=TEXTO_2)), tiling=dict(pad=3), maxdepth=3))
            fig.update_layout(height=H_M + 10, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=26, b=0),
                              font=dict(family="Inter, Helvetica, Arial, sans-serif", color=TEXTO_2),
                              hoverlabel=dict(bgcolor=ROXO_AMEIXA, bordercolor=BORDA_FORTE, font=dict(color=TEXTO)),
                              separators=",.", uniformtext=dict(minsize=10, mode="hide"))
            plot(fig)
            st.markdown(f'<div class="legenda-div"><span>{pct(media - desvio)}</span><div class="barra-div"></div>'
                        f'<span>{pct(media + desvio)}</span></div>'
                        f'<div class="nota" style="text-align:center">Margem de contribuição; centro da escala = '
                        f'média do recorte ({pct(media)})</div>', unsafe_allow_html=True)

    with card("margem_mes_canal"):
        c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c2[0]:
            cabecalho("Margem de contribuição por mês", "Marketplace comparado aos demais canais somados")
        todos = c2[1].toggle("Abrir todos os canais", key="canal_todos")
        grupo = df["canal"] if todos else np.where(df["canal"] == "Marketplace", "Marketplace", "Demais canais")
        cores_g = COR_CANAL if todos else {"Demais canais": COR_BASE, "Marketplace": COR_FOCO}
        tm = agregar(df.assign(grupo=grupo), ["grupo", "mes_rotulo"])["margem_pct"].unstack("grupo")
        fig = go.Figure()
        for gname in [x for x in cores_g if x in tm.columns]:
            fig.add_scatter(x=[str(i) for i in tm.index], y=tm[gname], name=gname, mode="lines+markers",
                            line=dict(color=cores_g[gname], width=2.5),
                            marker=dict(size=8, color=cores_g[gname], line=dict(color=ROXO_ESCURO, width=2)),
                            hovertemplate=f"{esc(gname)}: %{{y:.1f}}%<extra></extra>")
        fig.update_layout(hovermode="x unified")
        fig.update_yaxes(ticksuffix="%")
        plot(estilo(fig, H_M, legenda=True))

    with st.expander("Ver tabela por canal"):
        vis = tc[["pedidos", "receita", "margem_pct", "margem_real_pct", "ticket", "cmv_pct", "frete_pct",
                  "desconto_pct", "taxa_dev", "prazo"]].rename(columns={k2: METRICAS[k2]["nome"] for k2 in METRICAS})
        st.dataframe(vis.reset_index().rename(columns={"canal": "Canal"}), hide_index=True,
                     column_config={col: st.column_config.NumberColumn(col, format="localized") for col in vis.columns})

# ======================================================================
# DESCONTO
# ======================================================================
with abas[3]:
    fx = agregar(df, "faixa_desconto")
    fx["margem_pedido"] = fx["margem"] / fx["pedidos"]
    c = st.columns(2, gap="small")
    with c[0]:
        with card("margem_faixa_desc"):
            cabecalho("Margem por pedido, por faixa de desconto", "Margem de contribuição média por pedido")
            plot(colunas([str(i) for i in fx.index], fx["margem_pedido"], "brl2", altura=H_P,
                         hover_extra=[f"{inteiro(p)} pedidos" for p in fx["pedidos"]]))
    with c[1]:
        with card("itens_faixa_desc"):
            cabecalho("Itens por pedido, por faixa de desconto", "Quantidade média de itens")
            plot(colunas([str(i) for i in fx.index], fx["itens_pedido"], "dec", altura=H_P,
                         hover_extra=[f"{inteiro(p)} pedidos" for p in fx["pedidos"]]))
    rec = REC.get("Desconto")
    if rec:
        with card("insight_desconto"):
            insight(rec["texto"], rec["acao"])

    tmes = agregar(df, "mes_rotulo")
    tmes = tmes[tmes["pedidos"] > 0]
    c = st.columns(2, gap="small")
    with c[0]:
        with card("desconto_mes"):
            cabecalho("Desconto por mês", "Em % da receita bruta")
            pico = tmes["desconto_pct"].idxmax()
            plot(colunas([str(i) for i in tmes.index], tmes["desconto_pct"], "pct", foco={str(pico)}, altura=H_P,
                         rotulos=len(tmes) <= 13, hover_extra=[f"{inteiro(p)} pedidos" for p in tmes["pedidos"]]))
    with c[1]:
        with card("margem_mes"):
            cabecalho("Margem de contribuição por mês", "Em % da receita líquida")
            pior = str(tmes["margem_pct"].idxmin())
            fig = go.Figure(go.Scatter(
                x=[str(i) for i in tmes.index], y=tmes["margem_pct"], mode="lines+markers",
                line=dict(color=VIOLETA, width=2.5),
                marker=dict(size=9, line=dict(color=ROXO_ESCURO, width=2),
                            color=[COR_FOCO if str(i) == pior else COR_BASE for i in tmes.index]),
                hovertemplate="<b>%{x}</b><br>%{y:.2f}%<extra></extra>"))
            fig.add_annotation(x=pior, y=tmes.loc[tmes.index.astype(str) == pior, "margem_pct"].iloc[0],
                               text=pct(tmes["margem_pct"].min()), showarrow=False, yshift=-16,
                               font=dict(size=11, color=TEXTO))
            fig.update_yaxes(ticksuffix="%", tickformat=".1f")
            plot(estilo(fig, H_P))
    rec = REC.get("Sazonalidade")
    if rec:
        with card("insight_sazonal"):
            insight(rec["texto"], rec["acao"])

    with card("desc25_canal"):
        cabecalho("Pedidos com desconto acima de 25%, por canal", "Participação nos pedidos do canal")
        tcd = df.assign(acima=df["desconto_pct"] > 25).groupby("canal").agg(
            share=("acima", "mean"), pedidos=("acima", "sum"),
            valor=("desconto_reais", lambda s: s[df.loc[s.index, "desconto_pct"] > 25].sum()))
        tcd["share"] *= 100
        fig = barras_h(tcd, "share", "pct", foco={tcd["share"].idxmax()}, altura=H_P,
                       customdata=[[i, inteiro(tcd.loc[i, "pedidos"]), brl_c(tcd.loc[i, "valor"])]
                                   for i in tcd.sort_values("share").index])
        fig.update_traces(hovertemplate="<b>%{y}</b><br>%{x:.1f}% dos pedidos<br>%{customdata[1]} pedidos"
                                        "<br>%{customdata[2]} em desconto<extra></extra>")
        plot(fig)

# ======================================================================
# FRETE E ENTREGA
# ======================================================================
with abas[4]:
    c = st.columns(2, gap="small")
    with c[0]:
        with card("regra_frete"):
            cabecalho("Pedidos com frete grátis", "Por canal e faixa de ticket")
            grupo = np.select([df["canal"] == "Marketplace", df["receita_liquida"] >= 250],
                              ["Marketplace (qualquer ticket)", "Demais canais, ticket a partir de R$ 250"],
                              default="Demais canais, ticket abaixo de R$ 250")
            tg = df.assign(grupo=grupo).groupby("grupo").agg(gratis=("frete_gratis", "mean"), pedidos=("order_id", "count"))
            tg["gratis"] *= 100
            fig = barras_h(tg, "gratis", "pct", foco={"Marketplace (qualquer ticket)"}, altura=H_P - 60,
                           customdata=[[i, inteiro(tg.loc[i, "pedidos"])] for i in tg.sort_values("gratis").index])
            fig.update_traces(hovertemplate="<b>%{y}</b><br>%{x:.1f}% com frete grátis<br>%{customdata[1]} pedidos<extra></extra>")
            fig.update_xaxes(range=[0, 125])
            plot(fig)
            if set(tg["gratis"].round(6)) == {0.0, 100.0} and len(tg) == 3:
                nota("A regra observada é exata: frete grátis em 100% dos pedidos a partir de R$ 250 fora do "
                     "Marketplace e em nenhum pedido do Marketplace.")
            insight_do_tema("Frete")
    with c[1]:
        with card("prazo_canal"):
            cabecalho("Prazo médio de entrega por canal", "Dias entre pedido e entrega")
            tp = agregar(df, "canal")
            plot(barras_h(tp, "prazo", "dec", foco={tp["prazo"].idxmax()}, altura=H_P - 60))
            mk_ = df[df["canal"] == "Marketplace"]
            fora_ = df[df["canal"] != "Marketplace"]
            if len(mk_) and len(fora_):
                dif = mk_["tempo_entrega_real"].mean() - fora_["tempo_entrega_real"].mean()
                if dif >= 2:
                    at_mk = (mk_["motivo_devolucao"] == "Atraso na entrega").mean() * 100
                    at_fora = (fora_["motivo_devolucao"] == "Atraso na entrega").mean() * 100
                    insight(f"O Marketplace entrega em {num(mk_['tempo_entrega_real'].mean())} dias em média, "
                            f"{num(dif)} dias a mais que os demais canais. Devoluções por atraso: "
                            f"{pct(at_mk)} dos pedidos do Marketplace, contra {pct(at_fora)} nos demais.",
                            "Revisar o SLA logístico do Marketplace e acompanhar o prazo semanalmente.")

    ft = agregar(df, "faixa_ticket")
    c = st.columns(2, gap="small")
    with c[0]:
        with card("frete_ticket"):
            cabecalho("Frete por faixa de ticket", "Em % da receita líquida")
            plot(colunas([str(i) for i in ft.index], ft["frete_pct"], "pct", foco={str(ft.index[0])}, altura=H_P,
                         hover_extra=[f"{inteiro(p)} pedidos" for p in ft["pedidos"]]))
    with c[1]:
        with card("margem_ticket"):
            cabecalho("Margem de contribuição por faixa de ticket", "Em % da receita líquida")
            plot(colunas([str(i) for i in ft.index], ft["margem_pct"], "pct", foco={str(ft.index[0])}, altura=H_P,
                         hover_extra=[f"{inteiro(p)} pedidos" for p in ft["pedidos"]]))
    rec = REC.get("Ticket")
    if rec:
        with card("insight_ticket"):
            insight(rec["texto"], rec["acao"])

    eleg = df[df["mk_elegivel_nao_subsidiado"]]
    with card("frete_mk_mes"):
        if len(eleg):
            cabecalho("Frete pago pelo Marketplace em pedidos a partir de R$ 250",
                      f"Por mês. Total no período: {brl(eleg['custo_frete'].sum())} em {inteiro(len(eleg))} pedidos")
            tf = eleg.groupby("mes_rotulo", observed=True).agg(frete=("custo_frete", "sum"), pedidos=("order_id", "count"))
            fig = colunas([str(i) for i in tf.index], tf["frete"], "brl", altura=H_P, rotulos=len(tf) <= 13,
                          hover_extra=[f"{inteiro(p)} pedidos" for p in tf["pedidos"]])
            fig.update_traces(marker_color=COR_FOCO)
            plot(fig)
        else:
            cabecalho("Frete pago pelo Marketplace em pedidos a partir de R$ 250")
            nota("Não há pedidos do Marketplace a partir de R$ 250 no recorte atual.")

# ======================================================================
# DEVOLUÇÕES
# ======================================================================
with abas[5]:
    dev = df[df["devolvido"]]
    if dev.empty:
        with card("sem_dev"):
            cabecalho("Devoluções")
            nota("Não há pedidos devolvidos no recorte atual (verifique o filtro 'Incluir devolvidos').")
    else:
        c = st.columns(2, gap="small")
        with c[0]:
            with card("motivos"):
                cabecalho("Devoluções por motivo", "Pedidos devolvidos; defeito e atraso em destaque")
                tmv = dev.groupby("motivo_devolucao").agg(pedidos=("order_id", "count"),
                                                          custo=("custo_produto", "sum"), frete=("custo_frete", "sum"))
                tmv["custo"] += tmv["frete"]
                fig = barras_h(tmv, "pedidos", "int", foco=set(OPERACIONAIS), altura=H_P,
                               customdata=[[i, brl_c(tmv.loc[i, "custo"])] for i in tmv.sort_values("pedidos").index])
                fig.update_traces(hovertemplate="<b>%{y}</b><br>%{x:,.0f} pedidos<br>%{customdata[1]} em CMV e frete<extra></extra>")
                plot(fig)
                insight_do_tema("Devolução")
        with c[1]:
            with card("dev_prazo"):
                cabecalho("Taxa de devolução por prazo de entrega", "Pedidos devolvidos sobre pedidos da faixa")
                tpz = agregar(df, "faixa_prazo")
                plot(colunas([str(i) for i in tpz.index], tpz["taxa_dev"], "pct", altura=H_P,
                             hover_extra=[f"{inteiro(p)} pedidos" for p in tpz["pedidos"]]))
                curtas = df.loc[df["tempo_entrega_real"] <= 7, "devolvido"].mean() * 100
                longas = df.loc[df["tempo_entrega_real"] > 7, "devolvido"].mean() * 100
                if pd.notna(curtas) and pd.notna(longas):
                    if longas - curtas >= 0.5:
                        insight(f"Entregas acima de 7 dias têm devolução de {pct(longas)}, contra {pct(curtas)} nas de "
                                f"até 7 dias ({num(longas - curtas)} p.p.). A relação é fraca, mas consistente com o "
                                f"peso das devoluções por atraso.")
                    else:
                        insight(f"Sem diferença relevante entre entregas acima de 7 dias ({pct(longas)}) e até 7 dias "
                                f"({pct(curtas)}).")

        with card("dev_mapa"):
            cabecalho("Taxa de devolução por canal e categoria", "Em % dos pedidos de cada combinação; mais claro = maior")
            tq = agregar(df, ["canal", "categoria"])["taxa_dev"].unstack("categoria")
            tq = tq.reindex([ch for ch in COR_CANAL if ch in tq.index])[[x for x in COR_CATEGORIA if x in tq.columns]]
            fig = go.Figure(go.Heatmap(
                z=tq.values, x=list(tq.columns), y=list(tq.index), colorscale=ESCALA_SEQ, xgap=3, ygap=3,
                hovertemplate="<b>%{y}</b> · %{x}<br>%{z:.1f}%<extra></extra>",
                colorbar=dict(thickness=10, outlinewidth=0, ticksuffix="%", tickfont=dict(size=11, color=TEXTO_3))))
            rotular_celulas(fig, tq.values, list(tq.columns), list(tq.index), pct)
            fig.update_yaxes(autorange="reversed")
            fig = estilo(fig, H_M)
            fig.update_yaxes(tickfont=dict(size=12, color=TEXTO_2), showgrid=False)
            plot(fig)

# ======================================================================
# ATENDIMENTO
# ======================================================================
def tempo_txt(minutos):
    return f"{num(minutos, 0)} min" if minutos < 60 else f"{num(minutos / 60)} h"


with abas[6]:
    if ATD is None:
        with card("sac_sem_base"):
            cabecalho("Atendimento")
            nota("Base de atendimento não encontrada. Rode o tratamento com PROCESSAR_OUTRAS_BASES = True para "
                 "gerar atendimento_tratado.csv.")
    elif atd.empty:
        with card("sac_vazio"):
            cabecalho("Atendimento")
            nota("Nenhum chamado aberto no período selecionado.")
    else:
        pc, pm = tabelas_atendimento(atd)
        with card("sac_resumo"):
            cabecalho("Atendimento no período",
                      f"Chamados abertos de {ini:%d/%m/%Y} a {fim:%d/%m/%Y}. Aqui vale só o período: os filtros de "
                      "canal, categoria e pagamento não se aplicam, porque a base de chamados não se liga aos "
                      "pedidos de forma confiável.")
            pend = int(atd["pendente"].sum())
            itens_sac = [
                ("Chamados", inteiro(len(atd)),
                 f"{num(len(atd) / PED_PERIODO * 100)} por 100 pedidos aprovados" if PED_PERIODO else ""),
                ("Custo de atendimento", brl(atd["custo_operacional_ticket"].sum()),
                 f"{brl(atd['custo_operacional_ticket'].mean(), 2)} por chamado"),
                ("Satisfação média", f"{num(atd['nota_csat'].mean(), 2)} de 5",
                 f"{pct((atd['nota_csat'] <= 2).mean() * 100)} com nota 1 ou 2"),
                ("Primeira resposta", tempo_txt(atd["tempo_primeira_resposta_minutos"].median()),
                 "mediana, todos os canais"),
                ("Pendentes", inteiro(pend), f"{pct(pend / len(atd) * 100)} abertos ou em análise na extração"),
            ]
            st.markdown('<div class="stats">' + "".join(
                f'<div class="stat"><div class="r">{esc(r_)}</div><div class="v">{v_}</div>'
                f'<div class="r">{esc(s_)}</div></div>' for r_, v_, s_ in itens_sac) + "</div>",
                unsafe_allow_html=True)

        c = st.columns(2, gap="small")
        with c[0]:
            with card("sac_canal"):
                cabecalho("Custo de atendimento por canal de entrada", "Custo operacional dos chamados no período")
                ordem = pc.sort_values("custo").index
                fig = barras_h(pc, "custo", "brl", foco={pc["custo_chamado"].idxmax()}, altura=H_P,
                               customdata=[[i, inteiro(pc.loc[i, "chamados"]), brl(pc.loc[i, "custo_chamado"], 2),
                                            num(pc.loc[i, "csat"], 2)] for i in ordem])
                fig.update_traces(hovertemplate="<b>%{y}</b><br>Custo: R$ %{x:,.0f}<br>%{customdata[1]} chamados"
                                                "<br>%{customdata[2]} por chamado<br>Satisfação: %{customdata[3]}"
                                                "<extra></extra>")
                plot(fig)
                if len(pc) > 1:
                    caro, barato = pc["custo_chamado"].idxmax(), pc["custo_chamado"].idxmin()
                    insight(f"No {caro}, cada chamado custa {brl(pc.loc[caro, 'custo_chamado'], 2)}, contra "
                            f"{brl(pc.loc[barato, 'custo_chamado'], 2)} no {barato}. O {caro} recebe "
                            f"{pct(pc.loc[caro, 'part_chamados'])} dos chamados e gera "
                            f"{pct(pc.loc[caro, 'part_custo'])} do custo. A satisfação média é "
                            f"{num(pc.loc[caro, 'csat'], 2)} no {caro} e {num(pc.loc[barato, 'csat'], 2)} no {barato}.",
                            f"Direcionar os chamados de '{pm['chamados'].idxmax()}', o motivo mais frequente, para o "
                            f"{barato} e acompanhar o tempo de primeira resposta no {caro}.")
        with c[1]:
            with card("sac_csat"):
                cabecalho("Satisfação por motivo do chamado", "Nota média dada pelo cliente, de 1 a 5")
                ordem = pm.sort_values("csat").index
                fig = barras_h(pm, "csat", "dec", foco={pm["csat"].idxmin()}, altura=H_P,
                               customdata=[[i, inteiro(pm.loc[i, "chamados"]), pct(pm.loc[i, "part_chamados"])]
                                           for i in ordem])
                fig.update_traces(hovertemplate="<b>%{y}</b><br>Satisfação: %{x:.2f}<br>%{customdata[1]} chamados "
                                                "(%{customdata[2]})<extra></extra>")
                fig.update_xaxes(range=[0, 5.6])
                plot(fig)
                pior, maior = pm["csat"].idxmin(), pm["chamados"].idxmax()
                texto = (f"'{pior}' tem a menor satisfação, {num(pm.loc[pior, 'csat'], 2)}, e responde por "
                         f"{pct(pm.loc[pior, 'part_chamados'])} dos chamados.")
                if maior != pior:
                    texto += (f" O motivo mais frequente é '{maior}', com {pct(pm.loc[maior, 'part_chamados'])} "
                              f"do volume e nota {num(pm.loc[maior, 'csat'], 2)}.")
                insight(texto)

        c = st.columns(2, gap="small")
        with c[0]:
            with card("sac_mes"):
                cabecalho("Chamados por mês", "Chamados abertos; no detalhe, chamados por 100 pedidos aprovados do mês")
                ped_mes = BASE[(BASE["dia"] >= ini) & (BASE["dia"] <= fim)].groupby("ano_mes").size()
                ch_mes = atd.groupby(atd["data_abertura"].dt.strftime("%Y-%m")).size()
                tm_ = pd.DataFrame({"chamados": ch_mes, "pedidos": ped_mes}).fillna(0)
                tm_["por_100"] = tm_["chamados"] / tm_["pedidos"].replace(0, np.nan) * 100
                rot = [mes_rotulo(m) for m in tm_.index]
                plot(colunas(rot, tm_["chamados"], "int", foco={rot[int(np.argmax(tm_["chamados"].values))]},
                             altura=H_P, rotulos=len(tm_) <= 13,
                             hover_extra=[f"{num(v)} por 100 pedidos" if pd.notna(v) else "sem pedidos no mês"
                                          for v in tm_["por_100"]]))
                nota("Meses nas pontas do período podem estar incompletos.")
                validos = tm_[tm_["pedidos"] >= 100]
                if len(validos) >= 3:
                    acompanha = validos["chamados"].corr(validos["pedidos"]) >= 0.8
                    insight(("O volume de chamados acompanha o de pedidos: " if acompanha else "")
                            + f"de {num(validos['por_100'].min())} a {num(validos['por_100'].max())} chamados por "
                            f"100 pedidos, conforme o mês. O pico de chamados foi em "
                            f"{mes_rotulo(tm_['chamados'].idxmax(), extenso=True)}.")
        with c[1]:
            with card("sac_resposta"):
                cabecalho("Tempo até a primeira resposta, por canal de entrada", "Mediana, em horas")
                pc["resposta_h"] = pc["resposta_min"] / 60
                plot(barras_h(pc, "resposta_h", "dec", foco={pc["resposta_h"].idxmax()}, altura=H_P))
                lento = pc["resposta_h"].idxmax()
                insight(f"O {lento} leva {tempo_txt(pc.loc[lento, 'resposta_min'])} até a primeira resposta, em "
                        f"mediana, e tem {inteiro(pc.loc[lento, 'pendentes'])} chamados pendentes no período.")

        with st.expander("Ver chamados por motivo e canal de entrada"):
            cruz = pd.crosstab(atd["categoria_problema"], atd["canal_entrada"], margins=True, margins_name="Total")
            cruz.columns.name = None
            st.dataframe(cruz.reset_index().rename(columns={"categoria_problema": "Motivo"}), hide_index=True,
                         column_config={col: st.column_config.NumberColumn(col, format="localized")
                                        for col in cruz.columns})

# ======================================================================
# ALERTAS
# ======================================================================
ALERTAS = {
    "Margem negativa": lambda d: d["margem_negativa"],
    "Desconto acima de 30%": lambda d: d["desconto_pct"] > 30,
    "Marketplace pagando frete a partir de R$ 250": lambda d: d["mk_elegivel_nao_subsidiado"],
    "Devolução por defeito ou atraso": lambda d: d["devolvido"] & d["motivo_devolucao"].isin(OPERACIONAIS),
}
with abas[7]:
    with card("alertas"):
        cabecalho("Pedidos em alerta", "Lista para ação diária. Ordene pelo cabeçalho da tabela e exporte em CSV.")
        resumo = []
        for nome_a, regra in ALERTAS.items():
            sub = df[regra(df)]
            impacto = {"Margem negativa": sub["margem_contribuicao"].sum(),
                       "Desconto acima de 30%": sub["desconto_reais"].sum(),
                       "Marketplace pagando frete a partir de R$ 250": sub["custo_frete"].sum(),
                       "Devolução por defeito ou atraso": sub["custo_produto"].sum() + sub["custo_frete"].sum()}[nome_a]
            resumo.append(f'<div class="stat"><div class="r">{esc(nome_a)}</div>'
                          f'<div class="v">{inteiro(len(sub))} pedidos</div><div class="r">{brl_c(impacto)}</div></div>')
        st.markdown('<div class="stats">' + "".join(resumo) + "</div>", unsafe_allow_html=True)
        escolhidos = st.pills("Tipos de alerta", list(ALERTAS), selection_mode="multi", default=["Margem negativa"],
                              key="alertas_tipos")
        if escolhidos:
            mascara = pd.Series(False, index=df.index)
            motivos = pd.Series("", index=df.index)
            for nome_a in escolhidos:
                r = ALERTAS[nome_a](df)
                mascara |= r
                motivos = motivos.where(~r, motivos.where(motivos == "", motivos + "; ") + nome_a)
            lista = df[mascara].assign(alertas=motivos[mascara])
            nota(f"{inteiro(len(lista))} pedidos, ordenados da menor para a maior margem.")
            t = lista[["alertas"] + list(COLS_PEDIDO)].rename(columns={**COLS_PEDIDO, "alertas": "Alertas"})
            t = t.sort_values("Margem (R$)")
            cfg = {col: st.column_config.NumberColumn(col, format="localized") for col in t.columns if t[col].dtype.kind in "fi"}
            cfg["Data"] = st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY")
            st.dataframe(t, hide_index=True, height=440, column_config=cfg, key="alertas_df")
            st.download_button("Exportar CSV", csv_bytes(t), file_name="pedidos_em_alerta.csv", mime="text/csv",
                               key="alertas_csv")
        else:
            nota("Selecione ao menos um tipo de alerta.")

# ======================================================================
# SIMULADOR
# ======================================================================
with abas[8]:
    c = st.columns([1, 2], gap="small")
    with c[0]:
        with card("sim_controles"):
            cabecalho("Alavancas", "Os cálculos usam o recorte de filtros atual")
            lev_frete = st.slider("Frete do Marketplace a partir de R$ 250 subsidiado", 0, 100, 100, 5,
                                  format="%d%%", key="sim_frete")
            teto = st.slider("Teto de desconto por pedido", 10, 40, 25, 1, format="%d%%", key="sim_teto")
            adesao = st.slider("Adesão ao teto", 0, 100, 80, 5, format="%d%%", key="sim_adesao")
            red_dev = st.slider("Redução das devoluções por defeito ou atraso", 0, 100, 40, 5, format="%d%%",
                                key="sim_dev")
            nota("Premissas: o subsídio elimina o frete desses pedidos; o teto recupera a parte do desconto acima "
                 "dele, ponderada pela adesão, sem perda de volume; cada devolução evitada deixa de perder CMV e "
                 "frete. Valores referentes ao período filtrado.")
    ganho_frete = df.loc[df["mk_elegivel_nao_subsidiado"], "custo_frete"].sum() * lev_frete / 100
    m_teto = df["desconto_pct"] > teto
    ganho_desc = ((df.loc[m_teto, "desconto_pct"] - teto) / 100 * df.loc[m_teto, "receita_bruta"]).sum() * adesao / 100
    dev_op = df[df["devolvido"] & df["motivo_devolucao"].isin(OPERACIONAIS)]
    ganho_dev = (dev_op["custo_produto"].sum() + dev_op["custo_frete"].sum()) * red_dev / 100
    mc_nova = (K.margem + ganho_frete + ganho_desc) / K.receita * 100
    mr_nova = ((K.margem_real + ganho_frete + ganho_desc + ganho_dev) / K.receita_real * 100
               if K.receita_real else np.nan)
    with c[1]:
        with card("sim_resultado"):
            cabecalho("Resultado projetado")
            r = st.columns(3, gap="small")
            for col, rot, val, sub in [
                (r[0], "Margem de contribuição", pct(mc_nova, 2), f"Atual {pct(K.margem_pct, 2)} · +{num(mc_nova - K.margem_pct, 2)} p.p."),
                (r[1], "Margem realizada", pct(mr_nova, 2), f"Atual {pct(K.margem_real_pct, 2)} · +{num(mr_nova - K.margem_real_pct, 2)} p.p."),
                (r[2], "Ganho total no período", brl_c(ganho_frete + ganho_desc + ganho_dev),
                 f"{inteiro(len(dev_op) * red_dev / 100)} devoluções evitadas")]:
                col.markdown(f'<div class="stat"><div class="r">{esc(rot)}</div><div class="v">{val}</div>'
                             f'<div class="r">{sub}</div></div>', unsafe_allow_html=True)
            topo = K.margem_real + ganho_frete + ganho_desc + ganho_dev
            fig = go.Figure(go.Waterfall(
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["Margem realizada atual", "Subsídio de frete", "Teto de desconto", "Menos devoluções", "Projetada"],
                y=[K.margem_real, ganho_frete, ganho_desc, ganho_dev, topo],
                text=[brl_c(v) for v in [K.margem_real, ganho_frete, ganho_desc, ganho_dev, topo]],
                textposition="outside", textfont=dict(size=11, color=TEXTO_2),
                connector=dict(line=dict(color=BORDA_FORTE, width=1)),
                increasing=dict(marker=dict(color=BOM)), totals=dict(marker=dict(color=VIOLETA)),
                decreasing=dict(marker=dict(color=ROSA)), hovertemplate="%{x}: %{text}<extra></extra>"))
            fig.update_yaxes(range=[0, max(topo, K.margem_real) * 1.15], tickprefix="R$ ", tickformat="~s")
            plot(estilo(fig, H_M))
            nota("A ponte parte da margem realizada porque a alavanca de devoluções só existe nessa métrica. "
                 "Na margem de contribuição entram apenas frete e desconto.")

st.markdown('<div class="nota" style="margin-top:20px">Definições: margem de contribuição = receita líquida − CMV − '
            'frete, sobre pedidos aprovados. Margem realizada considera que pedidos devolvidos perdem a receita e '
            'mantêm CMV e frete. Fontes: vendas_tratada.csv (pedidos, com o cadastro de estoque) e '
            'atendimento_tratado.csv (chamados, recortados só pelo período).</div>', unsafe_allow_html=True)
