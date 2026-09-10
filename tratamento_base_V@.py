"""
Case Vértice Retail — Tratamento da base
Pessoa 2 (dados + dashboard)  —  versão 2

ARQUIVOS NECESSÁRIOS NO MESMO DIRETÓRIO
---------------------------------------
Obrigatório:
    vendas.xlsx        -> tudo que o dashboard e o business case usam
Opcional (só se for usar os indicadores dessas bases):
    atendimento.xlsx   -> volume/custo de chamados (tem encoding quebrado)
    clientes.xlsx      -> segmento RFM, LTV cadastrado
    estoque.xlsx       -> preço sugerido, custo unitário, disponibilidade
    marketing.xlsx     -> investimento, ROAS, CAC (NÃO reconciliável com vendas)

SAÍDAS
------
    vendas_tratada.csv       base de pedidos aprovados + colunas derivadas
    calendario_sazonal.csv   índice mensal de volume/receita/itens

DEFINIÇÃO DE MARGEM ADOTADA
---------------------------
    Oficial : margem_contribuicao sobre status_pagamento = "Aprovado"  -> 54,34%
    Ressalva: margem realizada, líquida de devolução                    -> 46,30%
              (usar helper margem_realizada_pct(), NÃO somar a coluna
               e dividir pela receita total — o denominador muda)
"""

import io
import os
import numpy as np
import pandas as pd

PROCESSAR_OUTRAS_BASES = False   # ligue se precisar de atendimento/clientes/estoque


# ======================================================================
# 1. LEITURA
# ======================================================================
# Os .xlsx do Data Room são CSV com extensão trocada: cada linha vem como
# uma única string na primeira coluna. read_excel direto devolve 1 coluna só.
def ler_base(caminho):
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"'{caminho}' não encontrado neste diretório.")
    raw = pd.read_excel(caminho, sheet_name=0, header=None)
    texto = "\n".join(raw[0].astype(str).tolist())
    return pd.read_csv(io.StringIO(texto))


def corrigir_encoding(serie):
    """Corrige UTF-8 lido como latin-1 (ex.: 'DÃºvida' -> 'Dúvida')."""
    return (serie.astype(str)
            .str.encode("latin-1", errors="ignore")
            .str.decode("utf-8", errors="ignore"))


vendas = ler_base("vendas.xlsx")
print(f"Linhas lidas: {len(vendas):,}")


# ======================================================================
# 2. LIMPEZA
# ======================================================================
antes = len(vendas)
vendas = vendas.dropna(subset=["quantidade"]).copy()      # ORD-072219
print(f"Linhas removidas por campos nulos: {antes - len(vendas)}")

vendas["data_pedido"] = pd.to_datetime(vendas["data_pedido"])

# devolvido vem como bool nativo; normaliza caso venha string em outra carga
if vendas["devolvido"].dtype == object:
    vendas["devolvido"] = (vendas["devolvido"]
                           .astype(str).str.strip().str.lower()
                           .map({"true": True, "false": False})
                           .fillna(vendas["devolvido"]))
vendas["devolvido"] = vendas["devolvido"].astype(bool)

dups = vendas["order_id"].duplicated().sum()
print(f"order_id duplicados: {dups}")


# ======================================================================
# 3. FILTRO OFICIAL
# ======================================================================
df = vendas[vendas["status_pagamento"] == "Aprovado"].copy()
print(f"Pedidos aprovados: {len(df):,} de {len(vendas):,}")


# ======================================================================
# 4. COLUNAS DERIVADAS
# ======================================================================
# --- Desconto ---------------------------------------------------------
df["desconto_pct"] = df["desconto_reais"] / df["receita_bruta"] * 100
df["tem_desconto"] = df["desconto_reais"] > 0
df["desconto_acima_25"] = df["desconto_pct"] > 25
df["faixa_desconto"] = pd.cut(
    df["desconto_pct"],
    bins=[-0.01, 0.01, 10, 20, 25, 30, np.inf],
    labels=["0%", "0-10%", "10-20%", "20-25%", "25-30%", ">30%"],
)

# --- Frete ------------------------------------------------------------
# Regra detectada: frete grátis acima de R$250, EXCETO no Marketplace
df["frete_gratis"] = df["custo_frete"] == 0
df["mk_elegivel_nao_subsidiado"] = (df["receita_liquida"] >= 250) & (df["canal"] == "Marketplace")

# --- Ticket -----------------------------------------------------------
df["faixa_ticket"] = pd.cut(
    df["receita_liquida"],
    bins=[0, 100, 200, 250, 300, 500, 1000, np.inf],
    labels=["<100", "100-200", "200-250", "250-300", "300-500", "500-1000", ">1000"],
)

# --- Componentes da margem (% da receita líquida) ---------------------
df["cmv_pct"] = df["custo_produto"] / df["receita_liquida"] * 100
df["frete_pct"] = df["custo_frete"] / df["receita_liquida"] * 100
df["desconto_sobre_bruta_pct"] = df["desconto_reais"] / df["receita_bruta"] * 100
df["margem_pct"] = df["margem_contribuicao"] / df["receita_liquida"] * 100
df["margem_negativa"] = df["margem_contribuicao"] < 0

# --- Tempo ------------------------------------------------------------
df["ano"] = df["data_pedido"].dt.year
df["mes"] = df["data_pedido"].dt.month
df["ano_mes"] = df["data_pedido"].dt.to_period("M").astype(str)

# --- Margem realizada (RESSALVA — ver helper abaixo) ------------------
# Por linha: devolvido perde a margem E os custos não voltam.
df["margem_realizada"] = np.where(
    df["devolvido"], -(df["custo_produto"] + df["custo_frete"]), df["margem_contribuicao"]
)
# Receita que de fato se realiza (zero para devolvidos) — necessária para
# calcular o PERCENTUAL corretamente.
df["receita_realizada"] = np.where(df["devolvido"], 0.0, df["receita_liquida"])


def margem_realizada_pct(dados):
    """% de margem realizada. NÃO usar receita_liquida no denominador."""
    rec = dados["receita_realizada"].sum()
    return np.nan if rec == 0 else dados["margem_realizada"].sum() / rec * 100


# ======================================================================
# 5. CALENDÁRIO SAZONAL (base 2023, único ano completo)
# ======================================================================
a23 = df[df["ano"] == 2023]
cal = a23.groupby("mes").agg(
    pedidos=("order_id", "count"),
    receita=("receita_liquida", "sum"),
    itens=("quantidade", "sum"),
    margem_abs=("margem_contribuicao", "sum"),
    receita_bruta=("receita_bruta", "sum"),
    desconto=("desconto_reais", "sum"),
)
cal["margem_pct"] = cal["margem_abs"] / cal["receita"] * 100
cal["desconto_pct"] = cal["desconto"] / cal["receita_bruta"] * 100
for col, novo in [("pedidos", "idx_pedidos"), ("receita", "idx_receita"), ("itens", "idx_itens")]:
    cal[novo] = (cal[col] / cal[col].mean() * 100).round(1)
cal["classificacao"] = cal["idx_pedidos"].apply(
    lambda i: "PICO" if i >= 140 else ("MEDIA" if i >= 90 else "VALE")
)
cal.index = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
cal.index.name = "mes"

# Índice sazonal aplicado por mês. Jan/2024 (1.066 pedidos) herda o índice
# de jan/2023 — aceitável, pois só existe um ano completo na base.
df["idx_sazonal"] = df["mes"].map(dict(zip(range(1, 13), cal["idx_pedidos"].values)))


# ======================================================================
# 6. OUTRAS BASES (opcional)
# ======================================================================
if PROCESSAR_OUTRAS_BASES:
    at = ler_base("atendimento.xlsx")
    for c in ["categoria_problema", "canal_entrada", "texto_cliente", "status_atendimento"]:
        if c in at.columns:
            at[c] = corrigir_encoding(at[c])
    at["data_abertura"] = pd.to_datetime(at["data_abertura"], errors="coerce")
    at.to_csv("atendimento_tratado.csv", index=False, encoding="utf-8-sig")
    print(f"atendimento_tratado.csv gerado ({len(at):,} linhas)")


# ======================================================================
# 7. SANITY CHECKS
# ======================================================================
print("\n--- SANITY CHECKS ---")
c1 = ((df["margem_contribuicao"] - (df["receita_liquida"] - df["custo_produto"] - df["custo_frete"])).abs() < 0.01).all()
c2 = ((df["receita_liquida"] - (df["receita_bruta"] - df["desconto_reais"])).abs() < 0.01).all()
c3 = ((df["receita_bruta"] - (df["quantidade"] * df["preco_unitario"])).abs() < 0.01).all()
print(f"margem = receita_liq - cmv - frete .......... {'OK' if c1 else 'FALHOU'}")
print(f"receita_liq = receita_bruta - desconto ...... {'OK' if c2 else 'FALHOU'}")
print(f"receita_bruta = qtd * preco_unit ............ {'OK' if c3 else 'FALHOU'}")
print(f"nulos em colunas críticas ................... "
      f"{'OK' if df[['receita_liquida','custo_produto','custo_frete','canal','categoria']].isnull().sum().sum()==0 else 'FALHOU'}")
print(f"período: {df['data_pedido'].min().date()} a {df['data_pedido'].max().date()}")

fora_alto = df[(df["canal"] != "Marketplace") & (df["receita_liquida"] >= 250)]
fora_baixo = df[(df["canal"] != "Marketplace") & (df["receita_liquida"] < 250)]
mk = df[df["canal"] == "Marketplace"]
print("\nRegra de frete (esperado 100 / 0 / 0):")
print(f"  fora MK, ticket >= 250 : {fora_alto['frete_gratis'].mean()*100:6.2f}%")
print(f"  fora MK, ticket <  250 : {fora_baixo['frete_gratis'].mean()*100:6.2f}%")
print(f"  Marketplace            : {mk['frete_gratis'].mean()*100:6.2f}%")


# ======================================================================
# 8. INDICADORES-CHAVE (business case)
# ======================================================================
R = df["receita_liquida"].sum()
M = df["margem_contribuicao"].sum()
print("\n--- INDICADORES ---")
print(f"Receita líquida ............. R$ {R:>14,.0f}")
print(f"Margem de contribuição ...... R$ {M:>14,.0f}   ({M/R*100:.2f}%)   <- OFICIAL")
print(f"Margem realizada (ressalva) . {margem_realizada_pct(df):.2f}%")
print(f"Desconto total .............. R$ {df['desconto_reais'].sum():>14,.0f}   ({df['desconto_reais'].sum()/df['receita_bruta'].sum()*100:.2f}% da rec. bruta)")
print(f"  acima de 25% .............. R$ {df[df['desconto_acima_25']]['desconto_reais'].sum():>14,.0f}   ({df['desconto_acima_25'].sum():,} pedidos)")
print(f"Frete total ................. R$ {df['custo_frete'].sum():>14,.0f}   ({df['custo_frete'].sum()/R*100:.2f}% da receita)")
print(f"  MK elegível não subsid. ... R$ {df[df['mk_elegivel_nao_subsidiado']]['custo_frete'].sum():>14,.0f}   ({df['mk_elegivel_nao_subsidiado'].sum():,} pedidos)")
print(f"Pedidos com margem negativa . {df['margem_negativa'].sum():,}")
print(f"Margem c/ desconto .......... {df[df['tem_desconto']]['margem_contribuicao'].sum()/df[df['tem_desconto']]['receita_liquida'].sum()*100:.2f}%")
print(f"Margem s/ desconto .......... {df[~df['tem_desconto']]['margem_contribuicao'].sum()/df[~df['tem_desconto']]['receita_liquida'].sum()*100:.2f}%")


# ======================================================================
# 9. EXPORTAÇÃO
# ======================================================================
df.to_csv("vendas_tratada.csv", index=False, encoding="utf-8-sig")
cal.round(2).to_csv("calendario_sazonal.csv", encoding="utf-8-sig")
print(f"\nGerados: vendas_tratada.csv ({len(df):,} linhas, {len(df.columns)} colunas) "
      f"e calendario_sazonal.csv")