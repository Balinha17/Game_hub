from __future__ import annotations

import re
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="FM Transferências",
    page_icon="💸",
    layout="wide"
)

URL_TRANSFERENCIAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQstFkeNnP5dKUnfHjl2UScwn2UnIHUuGuHqx0pJMlo86ovTeqMB6wZ3MvrGGwGPkxkWzRbdPFUV90y/pub?gid=1238900838&single=true&output=csv"

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
    .block-container {
        max-width: 1450px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    .hero {
        background: linear-gradient(135deg, #111827 0%, #1f2937 50%, #0f766e 100%);
        padding: 24px 28px;
        border-radius: 22px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 14px 34px rgba(0,0,0,0.22);
    }

    .hero h1 {
        margin: 0;
        font-size: 2rem;
    }

    .hero p {
        margin: 8px 0 0 0;
        color: #d1fae5;
        font-size: 1rem;
    }

    .kpi {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 18px;
        padding: 14px 16px;
        background: var(--secondary-background-color);
        min-height: 105px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .kpi-label {
        font-size: 0.92rem;
        opacity: 0.75;
        margin-bottom: 8px;
    }

    .kpi-value {
        font-size: 1.9rem;
        font-weight: 800;
        line-height: 1.05;
        color: var(--text-color);
        word-break: break-word;
    }

    .section-card {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 18px;
        padding: 16px;
        background: var(--secondary-background-color);
        margin-bottom: 18px;
    }

    .transfer-card {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 16px;
        padding: 12px 14px;
        background: var(--secondary-background-color);
        margin-bottom: 10px;
    }

    .transfer-player {
        font-size: 1.05rem;
        font-weight: 800;
        line-height: 1.2;
    }

    .transfer-meta {
        font-size: 0.92rem;
        opacity: 0.78;
        margin-top: 3px;
    }

    .transfer-value {
        font-size: 1.15rem;
        font-weight: 800;
        text-align: right;
        white-space: nowrap;
    }

    .pill-in {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        background: rgba(34, 197, 94, 0.16);
        color: rgb(22, 101, 52);
    }

    .pill-out {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        background: rgba(239, 68, 68, 0.15);
        color: rgb(153, 27, 27);
    }

    .window-title {
        font-size: 1.25rem;
        font-weight: 800;
        margin-bottom: 10px;
    }

    .window-subtitle {
        font-size: 0.92rem;
        opacity: 0.75;
        margin-bottom: 14px;
    }

    .col-header-in {
        font-size: 1rem;
        font-weight: 800;
        color: #22c55e;
        margin-bottom: 12px;
    }

    .col-header-out {
        font-size: 1rem;
        font-weight: 800;
        color: #ef4444;
        margin-bottom: 12px;
    }

    .ranking-title {
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: 12px;
    }

    .ranking-item {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 14px;
        padding: 12px 14px;
        background: var(--secondary-background-color);
        margin-bottom: 10px;
    }

    .ranking-pos {
        font-size: 0.82rem;
        font-weight: 800;
        opacity: 0.7;
        margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# HELPERS
# =========================================================
MESES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

MESES_ABREV = {
    "jan": 1,
    "fev": 2,
    "mar": 3,
    "abr": 4,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "out": 10,
    "nov": 11,
    "dez": 12,
}


def slugify(texto: str) -> str:
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    ren = {}
    for c in df.columns:
        novo = slugify(c).replace("_", " ")
        ren[c] = novo
    return df.rename(columns=ren)


def achar_coluna(df: pd.DataFrame, opcoes: list[str], obrigatoria: bool = True) -> str | None:
    for op in opcoes:
        if op in df.columns:
            return op
    if obrigatoria:
        raise KeyError(f"Coluna não encontrada. Esperado uma destas: {opcoes}")
    return None


def fmt_int(valor) -> str:
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return "0"


def limpar_texto(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def parse_valor_euro(valor) -> float:
    if pd.isna(valor):
        return 0.0

    s = str(valor).strip()
    if not s:
        return 0.0

    s = s.replace("€", "").replace("EUR", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")

    try:
        return float(s)
    except Exception:
        return 0.0


def fmt_num_pt(valor: float, casas: int = 2) -> str:
    try:
        s = f"{float(valor):,.{casas}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def fmt_moeda(valor) -> str:
    try:
        v = float(valor)
    except Exception:
        return "€0,00"

    abs_v = abs(v)

    if abs_v >= 1_000_000_000:
        return f"€{fmt_num_pt(v / 1_000_000_000, 2)} Bi"
    if abs_v >= 1_000_000:
        return f"€{fmt_num_pt(v / 1_000_000, 2)} Mi"

    return f"€{fmt_num_pt(v, 2)}"


def classificar_tipo_operacao(valor: str) -> str:
    s = slugify(valor).replace("_", " ")
    if s in ["entrada", "compra", "chegada", "contratacao", "contratacao definitiva"]:
        return "entrada"
    if s in ["saida", "venda", "emprestado", "liberado"]:
        return "saida"

    if "entrada" in s or "compra" in s:
        return "entrada"
    if "saida" in s or "venda" in s:
        return "saida"

    return s


def parse_janela_para_mes_ano(valor) -> tuple[int, int]:
    if pd.isna(valor):
        return (0, 0)

    if isinstance(valor, (pd.Timestamp, datetime)):
        return (int(valor.year), int(valor.month))

    s = limpar_texto(valor)
    if not s:
        return (0, 0)

    try:
        dt = pd.to_datetime(s, errors="raise", dayfirst=False)
        return (int(dt.year), int(dt.month))
    except Exception:
        pass

    s_low = s.lower()

    m = re.search(r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-zç]*/\s*((19|20)\d{2})", s_low)
    if m:
        mes_txt = m.group(1)[:3]
        ano = int(m.group(2))
        mes = MESES_ABREV.get(mes_txt, 0)
        return (ano, mes)

    for num_mes, nome_mes in MESES_PT.items():
        if nome_mes.lower() in s_low:
            m_ano = re.search(r"(19|20)\d{2}", s_low)
            if m_ano:
                return (int(m_ano.group()), num_mes)

    m_ano = re.search(r"(19|20)\d{2}", s_low)
    if m_ano:
        return (int(m_ano.group()), 0)

    return (0, 0)


def formatar_janela_pt(valor) -> str:
    ano, mes = parse_janela_para_mes_ano(valor)
    if ano and mes:
        return f"{MESES_PT[mes]}/{ano}"
    if ano:
        return str(ano)
    return limpar_texto(valor)


def ordem_janela_label(label: str) -> tuple[int, int, str]:
    ano, mes = parse_janela_para_mes_ano(label)
    return (ano, mes, str(label))


def resumo_janela(df_janela: pd.DataFrame) -> dict:
    entradas = df_janela[df_janela["tipo_operacao"] == "entrada"].copy()
    saidas = df_janela[df_janela["tipo_operacao"] == "saida"].copy()

    valor_entradas = entradas["valor_num"].sum()
    valor_saidas = saidas["valor_num"].sum()

    return {
        "qtd_entradas": len(entradas),
        "qtd_saidas": len(saidas),
        "valor_entradas": valor_entradas,
        "valor_saidas": valor_saidas,
        "saldo": valor_saidas - valor_entradas,
    }


def ordenar_df_cards(df_base: pd.DataFrame, ordenacao: str) -> pd.DataFrame:
    if df_base.empty:
        return df_base

    if ordenacao == "Maior valor":
        return df_base.sort_values(
            by=["valor_num", "ano", "mes_num", "jogador"],
            ascending=[False, False, False, True],
            kind="mergesort"
        )

    if ordenacao == "A-Z":
        return df_base.sort_values(
            by=["jogador", "ano", "mes_num"],
            ascending=[True, False, False],
            kind="mergesort"
        )

    return df_base.sort_values(
        by=["ano", "mes_num", "ordem_original"],
        ascending=[False, False, False],
        kind="mergesort"
    )


def render_transfer_card(row: pd.Series, tipo: str) -> None:
    jogador = limpar_texto(row["jogador"])
    clube = limpar_texto(row["clube"])
    valor = fmt_moeda(row["valor_num"])
    janela = limpar_texto(row["janela_label"])

    if tipo == "entrada":
        pill = '<span class="pill-in">Entrada</span>'
        meta = f"De: {clube}" if clube else "Origem não informada"
    else:
        pill = '<span class="pill-out">Saída</span>'
        meta = f"Para: {clube}" if clube else "Destino não informado"

    st.markdown(f"""
        <div class="transfer-card">
            <div style="display:flex; justify-content:space-between; gap:16px; align-items:flex-start;">
                <div>
                    <div class="transfer-player">{jogador}</div>
                    <div class="transfer-meta">{meta}</div>
                    <div class="transfer-meta">{janela}</div>
                    <div style="margin-top:8px;">{pill}</div>
                </div>
                <div class="transfer-value">{valor}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_ranking_item(row: pd.Series, posicao: int, tipo: str) -> None:
    jogador = limpar_texto(row["jogador"])
    clube = limpar_texto(row["clube"])
    janela = limpar_texto(row["janela_label"])
    valor = fmt_moeda(row["valor_num"])

    if tipo == "entrada":
        linha_clube = f"De: {clube}" if clube else "Origem não informada"
    else:
        linha_clube = f"Para: {clube}" if clube else "Destino não informado"

    st.markdown(f"""
        <div class="ranking-item">
            <div style="display:flex; justify-content:space-between; gap:16px; align-items:flex-start;">
                <div>
                    <div class="ranking-pos">#{posicao}</div>
                    <div class="transfer-player">{jogador}</div>
                    <div class="transfer-meta">{linha_clube}</div>
                    <div class="transfer-meta">{janela}</div>
                </div>
                <div class="transfer-value">{valor}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# =========================================================
# CARGA DOS DADOS - GOOGLE SHEETS
# =========================================================
@st.cache_data(ttl=60, show_spinner="Carregando transferências do Google Sheets...")
def carregar_transferencias() -> tuple[pd.DataFrame, dict[str, str]]:
    try:
        df = pd.read_csv(URL_TRANSFERENCIAS)
    except Exception as e:
        raise RuntimeError(f"Erro ao carregar a aba Transferências do Google Sheets: {e}")

    if df.empty:
        raise RuntimeError("A aba Transferências veio vazia do Google Sheets.")

    df = normalizar_colunas(df)

    cols = {
        "janela": achar_coluna(df, ["janela", "periodo", "período"]),
        "operacao": achar_coluna(df, ["operacao", "operação", "tipo", "movimento"]),
        "jogador": achar_coluna(df, ["jogador", "player", "atleta"]),
        "valor": achar_coluna(df, ["valor", "taxa", "fee"]),
        "clube": achar_coluna(df, ["clube", "time", "equipe", "origem destino"]),
    }

    df = df.rename(columns={
        cols["janela"]: "janela",
        cols["operacao"]: "operacao",
        cols["jogador"]: "jogador",
        cols["valor"]: "valor",
        cols["clube"]: "clube",
    }).copy()

    df["ordem_original"] = range(len(df))
    df["janela"] = df["janela"].astype(str).str.strip()
    df["operacao"] = df["operacao"].astype(str).str.strip()
    df["jogador"] = df["jogador"].astype(str).str.strip()
    df["clube"] = df["clube"].astype(str).str.strip()
    df["valor_num"] = df["valor"].apply(parse_valor_euro)
    df["tipo_operacao"] = df["operacao"].apply(classificar_tipo_operacao)

    df = df[df["jogador"].astype(str).str.strip() != ""].copy()

    df[["ano", "mes_num"]] = df["janela"].apply(lambda x: pd.Series(parse_janela_para_mes_ano(x)))
    df["janela_label"] = df["janela"].apply(formatar_janela_pt)

    return df, cols


try:
    df, cols_originais = carregar_transferencias()
except Exception as e:
    st.error(str(e))
    st.stop()

# =========================================================
# TOPO
# =========================================================
st.markdown("""
<div class="hero">
    <h1>💸 Transferências</h1>
    <p>Dados carregados diretamente do Google Sheets publicado como CSV.</p>
</div>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Filtros")

anos = sorted([a for a in df["ano"].dropna().unique().tolist() if a != 0])
anos_opcoes = ["Todos"] + anos
ano_selecionado = st.sidebar.selectbox("Ano", anos_opcoes, index=0)

janelas = sorted(df["janela_label"].dropna().unique().tolist(), key=ordem_janela_label)
janelas_selecionadas = st.sidebar.multiselect(
    "Janela específica",
    options=janelas,
    default=[]
)

busca = st.sidebar.text_input("Buscar jogador ou clube")

ordenacao = st.sidebar.selectbox(
    "Ordenar cards por",
    ["Mais recente", "Maior valor", "A-Z"]
)

# =========================================================
# FILTROS
# =========================================================
filtrado = df.copy()

if ano_selecionado != "Todos":
    filtrado = filtrado[filtrado["ano"] == ano_selecionado]

if janelas_selecionadas:
    filtrado = filtrado[filtrado["janela_label"].isin(janelas_selecionadas)]

if busca:
    termo = busca.strip()
    filtrado = filtrado[
        filtrado["jogador"].str.contains(termo, case=False, na=False)
        | filtrado["clube"].str.contains(termo, case=False, na=False)
    ]

if filtrado.empty:
    st.warning("Nenhuma transferência encontrada com os filtros atuais.")
    st.stop()

# =========================================================
# KPIs GERAIS
# =========================================================
entradas_geral = filtrado[filtrado["tipo_operacao"] == "entrada"].copy()
saidas_geral = filtrado[filtrado["tipo_operacao"] == "saida"].copy()

valor_entradas_geral = entradas_geral["valor_num"].sum()
valor_saidas_geral = saidas_geral["valor_num"].sum()
saldo_geral = valor_saidas_geral - valor_entradas_geral

k1, k2, k3, k4, k5 = st.columns(5)

kpis = [
    ("Contratações", fmt_int(len(entradas_geral))),
    ("Vendas", fmt_int(len(saidas_geral))),
    ("Gasto total", fmt_moeda(valor_entradas_geral)),
    ("Receita total", fmt_moeda(valor_saidas_geral)),
    ("Saldo", fmt_moeda(saldo_geral)),
]

for col, (label, value) in zip([k1, k2, k3, k4, k5], kpis):
    with col:
        st.markdown(f"""
        <div class="kpi">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# RANKING FIXO
# =========================================================
st.markdown("<br>", unsafe_allow_html=True)

top_compras = entradas_geral.sort_values(
    by=["valor_num", "ano", "mes_num", "jogador"],
    ascending=[False, False, False, True],
    kind="mergesort"
).head(3)

top_vendas = saidas_geral.sort_values(
    by=["valor_num", "ano", "mes_num", "jogador"],
    ascending=[False, False, False, True],
    kind="mergesort"
).head(3)

r1, r2 = st.columns(2)

with r1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="ranking-title" style="color:#22c55e;">TOP 3 COMPRAS MAIS CARAS</div>', unsafe_allow_html=True)
    if top_compras.empty:
        st.info("Nenhuma contratação encontrada no recorte atual.")
    else:
        for i, (_, row) in enumerate(top_compras.iterrows(), start=1):
            render_ranking_item(row, i, "entrada")
    st.markdown("</div>", unsafe_allow_html=True)

with r2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="ranking-title" style="color:#ef4444;">TOP 3 VENDAS MAIS CARAS</div>', unsafe_allow_html=True)
    if top_vendas.empty:
        st.info("Nenhuma venda encontrada no recorte atual.")
    else:
        for i, (_, row) in enumerate(top_vendas.iterrows(), start=1):
            render_ranking_item(row, i, "saida")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# AGRUPAMENTO POR JANELA
# =========================================================
janelas_filtradas = sorted(
    filtrado["janela_label"].dropna().unique().tolist(),
    key=ordem_janela_label
)

entradas_global = ordenar_df_cards(
    filtrado[filtrado["tipo_operacao"] == "entrada"].copy(),
    ordenacao
)
saidas_global = ordenar_df_cards(
    filtrado[filtrado["tipo_operacao"] == "saida"].copy(),
    ordenacao
)

for janela in janelas_filtradas:
    df_janela = filtrado[filtrado["janela_label"] == janela].copy()

    resumo = resumo_janela(df_janela)

    if ordenacao == "Maior valor":
        entradas = entradas_global[entradas_global["janela_label"] == janela].copy()
        saidas = saidas_global[saidas_global["janela_label"] == janela].copy()
    else:
        entradas = ordenar_df_cards(
            df_janela[df_janela["tipo_operacao"] == "entrada"].copy(),
            ordenacao
        )
        saidas = ordenar_df_cards(
            df_janela[df_janela["tipo_operacao"] == "saida"].copy(),
            ordenacao
        )

    st.markdown(f"""
    <div class="section-card">
        <div class="window-title">{janela}</div>
        <div class="window-subtitle">
            Entradas: {resumo['qtd_entradas']} •
            Saídas: {resumo['qtd_saidas']} •
            Gasto: {fmt_moeda(resumo['valor_entradas'])} •
            Receita: {fmt_moeda(resumo['valor_saidas'])} •
            Saldo: {fmt_moeda(resumo['saldo'])}
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="col-header-in">TRANSFERÊNCIAS DE ENTRADA</div>', unsafe_allow_html=True)
        if entradas.empty:
            st.info("Nenhuma contratação nesta janela.")
        else:
            for _, row in entradas.iterrows():
                render_transfer_card(row, "entrada")

    with c2:
        st.markdown('<div class="col-header-out">TRANSFERÊNCIAS DE SAÍDA</div>', unsafe_allow_html=True)
        if saidas.empty:
            st.info("Nenhuma venda nesta janela.")
        else:
            for _, row in saidas.iterrows():
                render_transfer_card(row, "saida")

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# TABELA FINAL
# =========================================================
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Tabela completa")

tabela = ordenar_df_cards(filtrado.copy(), ordenacao)

tabela["Tipo"] = tabela["tipo_operacao"].map({
    "entrada": "Entrada",
    "saida": "Saída"
}).fillna(tabela["operacao"])

tabela["Valor"] = tabela["valor_num"].apply(fmt_moeda)

tabela = tabela[["janela_label", "Tipo", "jogador", "clube", "Valor"]].rename(columns={
    "janela_label": "Janela",
    "jogador": "Jogador",
    "clube": "Clube"
})

st.dataframe(
    tabela,
    use_container_width=True,
    hide_index=True,
    height=500
)
