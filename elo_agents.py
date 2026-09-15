"""
Integração do painel com o Elo Agents.

O Elo Agents é um gateway com API no formato da OpenAI (modelos Claude via Amazon Bedrock):
usa a biblioteca oficial `openai`, trocando apenas o `base_url`.

Configuração, lida na hora de cada chamada (nunca congelada na importação do módulo):
    ELOAGENTS_API_KEY    chave do gateway (obrigatória)
    ELOAGENTS_BASE_URL   padrão https://chat.eloagents.click/api
    ELOAGENTS_MODELO     padrão claude-sonnet-46
Procuradas primeiro em st.secrets (.streamlit/secrets.toml ou segredos do deploy) e depois
em variáveis de ambiente.

Diagnóstico da conexão:
    python elo_agents.py
"""

import json
import os
import re
import sys
import time

BASE_URL_PADRAO = "https://chat.eloagents.click/api"
MODELO_PADRAO = "claude-sonnet-46"
TEMAS = ("Frete", "Desconto", "Ticket", "Devolução", "Sazonalidade", "Canais", "Mix", "Operação",
         "Margem", "Receita", "Volume", "Prazo", "Categoria", "Pagamento", "Produto", "Atendimento", "Estoque")
PRIORIDADES = ("alta", "média", "baixa")


class ErroElo(Exception):
    """Falha ao consultar o Elo Agents, com um tipo estável para a interface escolher a mensagem."""

    def __init__(self, tipo, mensagem, bruto=None):
        super().__init__(mensagem)
        self.tipo = tipo
        self.mensagem = mensagem
        self.bruto = bruto


# ----------------------------------------------------------------------
# Configuração e cliente
# ----------------------------------------------------------------------
def _config(nome, padrao=None):
    try:
        import streamlit as st
        if nome in st.secrets:
            return str(st.secrets[nome])
    except Exception:  # sem Streamlit ou sem arquivo de segredos
        pass
    return os.getenv(nome, padrao)


def chave():
    valor = _config("ELOAGENTS_API_KEY")
    return valor.strip() if valor and valor.strip() else None


def base_url():
    return _config("ELOAGENTS_BASE_URL", BASE_URL_PADRAO)


def modelo_padrao():
    return _config("ELOAGENTS_MODELO", MODELO_PADRAO)


def configurado():
    return chave() is not None


def cliente():
    k = chave()
    if not k:
        raise ErroElo("sem_chave", "ELOAGENTS_API_KEY não está definida.")
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ErroElo("dependencia", "A biblioteca openai não está instalada (pip install -r requirements.txt).") from e
    return OpenAI(api_key=k, base_url=base_url(), timeout=120, max_retries=1)


def _traduzir(erro):
    import openai
    # APITimeoutError é subclasse de APIConnectionError: precisa vir antes dela.
    mapa = [
        ((openai.AuthenticationError, openai.PermissionDeniedError), "chave",
         "O Elo Agents recusou a chave. Confira ELOAGENTS_API_KEY."),
        ((openai.NotFoundError,), "modelo", "Modelo ou endereço não encontrado no Elo Agents."),
        ((openai.RateLimitError,), "limite", "Limite de uso do Elo Agents atingido. Tente de novo em instantes."),
        ((openai.APITimeoutError,), "tempo", "O Elo Agents demorou mais de 120 segundos para responder."),
        ((openai.APIConnectionError,), "conexao", "Sem conexão com o Elo Agents. Verifique a rede e ELOAGENTS_BASE_URL."),
        ((openai.BadRequestError,), "requisicao", "O Elo Agents rejeitou a requisição."),
    ]
    for tipos, tipo, mensagem in mapa:
        if isinstance(erro, tipos):
            return ErroElo(tipo, mensagem, getattr(erro, "message", None) or str(erro))
    return ErroElo("desconhecido", f"Erro inesperado ao consultar o Elo Agents ({type(erro).__name__}).", str(erro))


def listar_modelos():
    try:
        return sorted(m.id for m in cliente().models.list().data)
    except ErroElo:
        raise
    except Exception as e:
        raise _traduzir(e) from e


# ----------------------------------------------------------------------
# Prompt
# ----------------------------------------------------------------------
SISTEMA = """Você é analista sênior de rentabilidade de varejo e apoia a diretoria comercial da Vértice Retail.
Você recebe um JSON com indicadores já calculados sobre o recorte de dados que o usuário filtrou no painel.

Regras:
1. Use apenas os dados do JSON. Não invente números, metas, benchmarks de mercado nem causas que os dados não mostrem.
2. Todo número citado precisa existir no JSON, com o mesmo arredondamento ou com uma casa decimal a menos. Não faça contas novas: se precisar de uma diferença ou participação, use as que já vêm calculadas.
3. Quando algo for hipótese ou interpretação, diga explicitamente que é uma hipótese.
4. Cada ação recomendada deve ser concreta, executável por um gestor e ligada ao dado que a justifica.
5. "valor_em_jogo" só deve ser preenchido com um valor em reais copiado do JSON que represente custo, perda ou oportunidade ligada à ação (por exemplo frete pago, desconto concedido ou excedente, CMV e frete perdidos em devoluções); informe o caminho do campo em "base_do_valor". Nunca use receita, margem ou totais de vendas como valor em jogo: nesses casos use null.
6. Escreva em português do Brasil, com frases diretas, sem jargão, sem emojis e sem travessões.
7. Se "amostra_pequena" for true, avise no resumo e seja cauteloso nas conclusões.
8. Se houver uma pergunta do usuário, priorize respondê-la; os insights devem servir a essa pergunta.
9. "atendimento_sac" vem de outra base e não se liga aos pedidos: analise chamados só por canal de entrada, motivo, custo, satisfação e tempo de resposta. Não relacione chamados a canais de venda, categorias, produtos ou devoluções, não compare motivos de chamado com motivos de devolução (o "Defeito" do SAC não é a devolução por defeito) e não junte atendimento e vendas no mesmo insight.
10. "por_situacao_atual_do_estoque" e "skus_de_maior_receita_no_recorte_com_estoque_atual_em_ruptura_ou_critico" mostram a posição do estoque na extração, não na data das vendas. As vendas desses SKUs são do período do recorte, não são recentes nem do dia da extração. Use só como risco de reposição, nunca como causa de resultados de vendas.

Responda somente com JSON válido, sem nenhum texto antes ou depois, neste formato:
{"resumo": "2 a 3 frases com a leitura geral do recorte",
 "insights": [
  {"tema": "Frete | Desconto | Ticket | Devolução | Sazonalidade | Canais | Mix | Operação | Atendimento | Estoque",
   "titulo": "até 70 caracteres",
   "texto": "2 a 3 frases com a evidência",
   "acao": "ação recomendada",
   "valor_em_jogo": 12345.67,
   "base_do_valor": "caminho.do.campo.no.json",
   "prioridade": "alta | média | baixa"}
 ]}
Gere de 3 a 6 insights, do mais para o menos relevante."""


INSTRUCOES_TABELA = """Você é analista sênior de rentabilidade de varejo e apoia a diretoria comercial da Vértice Retail.
Você recebe um JSON com as tabelas que o usuário está vendo agora na aba "Explorar dados" do painel. Elas foram montadas a partir da dimensão, da métrica e da quebra que ele escolheu, sobre o recorte filtrado, e mudam a cada escolha.

Tarefa: gerar insights sobre a métrica que o usuário escolheu ("configuracao.metrica_foco"), na dimensão escolhida ("configuracao.dimensao") e, quando houver, na quebra ("configuracao.quebra"). Esse é o assunto da análise.

Como proceder:
- Comece pela métrica foco: use "resumo_da_metrica_foco" e "ranking_da_metrica_foco" para apontar líderes, lanternas e a distância entre eles. As comparações já vêm calculadas ("diferenca_vs_total", "diferenca_vs_total_pp", "participacao_no_total_pct", "amplitude"): cite esses campos e não calcule outras diferenças, somas, médias ou percentuais. "configuracao.maior_valor_e_melhor" diz se um valor alto é bom ou ruim.
- Se houver "matriz_do_grafico", pelo menos dois insights devem vir dela: combinações que se destacam (use "matriz_do_grafico.resumo") e linhas ou colunas que fogem do padrão.
- Se houver "tabela_pedidos_da_selecao", pelo menos um insight deve descrever o que os pedidos selecionados têm em comum em relação à métrica foco.
- As outras colunas só podem aparecer para explicar um padrão da métrica foco, nunca como assunto principal de um insight. Não desvie a análise para frete ou desconto se a métrica foco não for de frete ou de desconto.
- Todo título deve nomear a métrica foco ou a dimensão analisada.

Regras:
1. Use apenas os dados do JSON. Não traga conhecimento externo, metas, benchmarks nem causas que as tabelas não mostrem.
2. Todo número citado precisa existir no JSON, com o mesmo arredondamento ou com uma casa decimal a menos. Não faça contas novas, nem diferenças nem médias.
3. Linhas com menos de 30 pedidos são amostra pequena: diga isso ao citá-las e seja cauteloso.
4. Quando algo for hipótese ou interpretação, diga explicitamente que é uma hipótese.
5. Cada ação recomendada deve ser concreta e ligada à linha ou ao grupo da tabela que a justifica.
6. "valor_em_jogo" só deve ser preenchido com um valor em reais copiado das tabelas que represente custo, perda ou oportunidade ligada à ação; informe o caminho em "base_do_valor". Nunca use receita, margem ou totais de vendas como valor em jogo: nesses casos use null.
7. Escreva em português do Brasil, com frases diretas, sem jargão, sem emojis e sem travessões.

Responda somente com JSON válido, sem nenhum texto antes ou depois, neste formato:
{"resumo": "2 a 3 frases com a leitura geral das tabelas",
 "insights": [
  {"tema": "o assunto do insight, alinhado à métrica ou à dimensão analisada: Margem | Receita | Volume | Ticket | Frete | Desconto | Devolução | Prazo | Canais | Categoria | Pagamento | Produto | Sazonalidade | Mix | Estoque",
   "titulo": "até 70 caracteres, nomeando a métrica foco ou a dimensão",
   "texto": "2 a 3 frases com a evidência tirada das tabelas",
   "acao": "ação recomendada",
   "valor_em_jogo": 12345.67,
   "base_do_valor": "caminho.do.campo.no.json",
   "prioridade": "alta | média | baixa"}
 ]}
Gere de 3 a 5 insights, do mais para o menos relevante."""


def _mensagem_usuario(instrucoes, pedido, contexto):
    dados = json.dumps(contexto, ensure_ascii=False, separators=(",", ":"))
    # As instruções vão na mensagem do usuário, e não num papel "system": o gateway do Elo Agents
    # injeta um prompt de sistema próprio com ferramentas (skills), e um "system" adicional fazia o
    # modelo responder com tool_calls e conteúdo vazio.
    return f"{instrucoes}\n\n{pedido}\n\nDados do recorte (JSON):\n{dados}"


# ----------------------------------------------------------------------
# Leitura da resposta
# ----------------------------------------------------------------------
def extrair_json(texto):
    """Aceita JSON puro ou envolto em bloco de código, com ou sem texto em volta."""
    t = (texto or "").strip()
    inicio, fim = t.find("{"), t.rfind("}")
    if inicio < 0 or fim <= inicio:
        raise ErroElo("formato", "A resposta do Elo Agents não veio no formato JSON esperado.", texto)
    try:
        return json.loads(t[inicio:fim + 1])
    except json.JSONDecodeError as e:
        raise ErroElo("formato", "A resposta do Elo Agents veio com JSON inválido.", texto) from e


def _normalizar(dados, bruto):
    itens = dados.get("insights") if isinstance(dados, dict) else None
    if not isinstance(itens, list):
        raise ErroElo("formato", "A resposta do Elo Agents não trouxe a lista de insights.", bruto)
    saida = []
    for item in itens[:6]:
        if not isinstance(item, dict):
            continue
        tema = str(item.get("tema", "")).strip()
        prioridade = str(item.get("prioridade", "")).strip().lower().replace("media", "média")
        valor = item.get("valor_em_jogo")
        try:
            valor = float(valor) if valor not in (None, "") else None
        except (TypeError, ValueError):
            valor = None
        saida.append(dict(
            tema=tema if tema in TEMAS else "Operação",
            titulo=str(item.get("titulo", "")).strip() or "Insight",
            texto=str(item.get("texto", "")).strip(),
            acao=str(item.get("acao", "")).strip(),
            valor=valor,
            base_valor=str(item.get("base_do_valor") or "").strip(),
            prioridade=prioridade if prioridade in PRIORIDADES else "média",
        ))
    if not saida:
        raise ErroElo("formato", "A resposta do Elo Agents veio sem insights.", bruto)
    return saida


# ----------------------------------------------------------------------
# Conferência de números: todo número citado precisa existir nos dados enviados
# ----------------------------------------------------------------------
_NUMERO = re.compile(
    r"(?<![\w/,.])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)(?![\w/]|[.,]\d)"
    r"(\s*(?:mil\b|mi\b|milhões|milhão|bi\b))?",
    re.IGNORECASE)
_ESCALA = {"mil": 1e3, "mi": 1e6, "milhão": 1e6, "milhões": 1e6, "bi": 1e9}


def _numeros_no_texto(texto, todos=False):
    achados = []
    for m in _NUMERO.finditer(texto or ""):
        bruto, sufixo = m.group(1), (m.group(2) or "").strip().lower()
        casas = len(bruto.split(",")[1]) if "," in bruto else 0
        valor = float(bruto.replace(".", "").replace(",", "."))
        escala = _ESCALA.get(sufixo, 1.0)
        if not todos and escala == 1.0 and casas == 0 and (valor <= 31 or 2000 <= valor <= 2100):
            continue  # dias, contagens pequenas, limiares e anos
        achados.append((m.group(0).strip(), valor * escala, 0.5 * 10 ** (-casas) * escala))
    return achados


def numeros_do_contexto(obj, saida=None):
    """Números de referência: valores numéricos e também os escritos em textos e nomes de chave
    (faixas como 'R$ 100–200', prazos como '8 a 10 dias')."""
    saida = [] if saida is None else saida
    if isinstance(obj, bool):
        return saida
    if isinstance(obj, (int, float)):
        saida.append(abs(float(obj)))
    elif isinstance(obj, str):
        saida.extend(abs(valor) for _, valor, _ in _numeros_no_texto(obj, todos=True))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            numeros_do_contexto(k, saida)
            numeros_do_contexto(v, saida)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            numeros_do_contexto(v, saida)
    return saida


def _existe(valor, tolerancia, referencias):
    return any(abs(r - valor) <= max(tolerancia, 0.005 * r) for r in referencias)


def numeros_nao_conferidos(texto, referencias):
    faltam = [rotulo for rotulo, valor, tol in _numeros_no_texto(texto) if not _existe(abs(valor), tol, referencias)]
    return list(dict.fromkeys(faltam))


# ----------------------------------------------------------------------
# Chamada principal
# ----------------------------------------------------------------------
def _completar(modelo, conteudo):
    # Sem max_tokens: o gateway descarta o parâmetro (dropped_compat_plugin_params).
    try:
        resposta = cliente().chat.completions.create(model=modelo, temperature=0,
                                                     messages=[{"role": "user", "content": conteudo}])
    except ErroElo:
        raise
    except Exception as e:
        raise _traduzir(e) from e
    texto = (resposta.choices[0].message.content or "") if resposta.choices else ""
    return resposta, texto


def gerar_insights(contexto, pergunta=None, modelo=None):
    """Insights gerais do recorte, opcionalmente guiados por uma pergunta do usuário."""
    pedido = (f"Pergunta do usuário: {pergunta}" if pergunta
              else "Gere os principais insights e ações recomendadas para este recorte.")
    return _gerar(SISTEMA, pedido, contexto, modelo)


def gerar_insights_tabela(contexto, modelo=None, pergunta=None):
    """Insights restritos às tabelas que o usuário está vendo na aba Explorar, focados na
    dimensão, na métrica e na quebra escolhidas e, opcionalmente, numa pergunta do usuário."""
    cfg = contexto.get("configuracao", {})
    quebra = cfg.get("quebra")
    pedido = (f'Analise a métrica "{cfg.get("metrica_foco")}" por "{cfg.get("dimensao")}"'
              + (f', com quebra por "{quebra}"' if quebra and quebra != "Nenhuma" else "")
              + ". Todos os insights devem ser sobre essa visão.")
    if pergunta:
        pedido += (f"\n\nPergunta do usuário: {pergunta}\nResponda a essa pergunta com os insights, usando só as "
                   "tabelas. Se as tabelas não tiverem os dados necessários para responder, diga isso no resumo "
                   "e indique qual dimensão, métrica ou quebra do painel ajudaria.")
    return _gerar(INSTRUCOES_TABELA, pedido, contexto, modelo)


def _gerar(instrucoes, pedido, contexto, modelo):
    modelo = modelo or modelo_padrao()
    conteudo = _mensagem_usuario(instrucoes, pedido, contexto)
    inicio = time.time()
    resposta, texto = _completar(modelo, conteudo)
    if not texto.strip():
        # O modelo pode tentar acionar uma ferramenta do gateway em vez de responder: insiste uma vez.
        resposta, texto = _completar(
            modelo, conteudo + "\n\nNão use ferramentas nem skills. Responda diretamente com o JSON pedido.")
    if not texto.strip():
        motivo = resposta.choices[0].finish_reason if resposta.choices else None
        if motivo == "tool_calls":
            raise ErroElo("ferramenta", "O modelo tentou acionar ferramentas do Elo Agents em vez de responder. "
                                        "Tente de novo ou escolha outro modelo.", "finish_reason=tool_calls")
        raise ErroElo("vazio", "O Elo Agents devolveu uma resposta vazia. Tente de novo.", f"finish_reason={motivo}")
    dados = extrair_json(texto)
    insights = _normalizar(dados, texto)

    referencias = numeros_do_contexto(contexto)
    for item in insights:
        # Regra do prompt reforçada no código: receita e margem nunca são valor em jogo (o modelo às
        # vezes usava a receita de SKUs em ruptura como se fosse perda).
        if item["valor"] is not None and re.search(r"receita|margem", item["base_valor"], re.IGNORECASE):
            item["valor"], item["base_valor"] = None, ""
        item["nao_conferidos"] = numeros_nao_conferidos(" ".join([item["titulo"], item["texto"], item["acao"]]),
                                                        referencias)
        if item["valor"] is not None and not _existe(abs(item["valor"]), 1.0, referencias):
            item["nao_conferidos"].append("valor em jogo")
    resumo = str(dados.get("resumo", "")).strip() if isinstance(dados, dict) else ""
    uso = getattr(resposta, "usage", None)
    return dict(insights=insights, resumo=resumo, resumo_nao_conferidos=numeros_nao_conferidos(resumo, referencias),
                modelo=modelo, segundos=time.time() - inicio, bruto=texto,
                tokens=getattr(uso, "total_tokens", None) if uso else None)


if __name__ == "__main__":
    print("Endereço:", base_url())
    print("Chave definida:", "sim" if configurado() else "não")
    try:
        print("Modelos disponíveis:", ", ".join(listar_modelos()))
        teste = cliente().chat.completions.create(model=modelo_padrao(), temperature=0,
                                                  messages=[{"role": "user", "content": "responda apenas: ok"}])
        print("Resposta de teste:", teste.choices[0].message.content)
    except ErroElo as e:
        print(f"Falha ({e.tipo}): {e.mensagem}")
        sys.exit(1)
    except Exception as e:  # erro fora do mapa acima
        print(f"Falha: {_traduzir(e).mensagem}")
        sys.exit(1)
