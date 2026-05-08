from __future__ import annotations

from pathlib import Path
import re
import unicodedata

import pandas as pd
import streamlit as st

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Estatística de Jogadores",
    page_icon="📊",
    layout="wide"
)

URL_STATS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQstFkeNnP5dKUnfHjl2UScwn2UnIHUuGuHqx0pJMlo86ovTeqMB6wZ3MvrGGwGPkxkWzRbdPFUV90y/pub?gid=1324969635&single=true&output=csv"

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
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 45%, #0f766e 100%);
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
        color: #dbeafe;
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
        font-size: 1.85rem;
        font-weight: 800;
        line-height: 1.05;
        color: var(--text-color);
    }

    .section-card {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 18px;
        padding: 16px;
        background: var(--secondary-background-color);
        margin-bottom: 18px;
    }

    .ranking-title {
        font-size: 1.02rem;
        font-weight: 800;
        margin-bottom: 10px;
    }

    .ranking-item {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 12px;
        padding: 10px 12px;
        background: var(--secondary-background-color);
        margin-bottom: 8px;
    }

    .ranking-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 12px;
    }

    .ranking-left {
        display: flex;
        align-items: baseline;
        gap: 10px;
        min-width: 0;
    }

    .ranking-pos-inline {
        font-size: 0.95rem;
        font-weight: 900;
        opacity: 0.75;
        flex-shrink: 0;
    }

    .ranking-name {
        font-size: 1.12rem;
        font-weight: 900;
        line-height: 1.2;
        word-break: break-word;
    }

    .ranking-value-big {
        font-size: 1.3rem;
        font-weight: 900;
        line-height: 1;
        white-space: nowrap;
        flex-shrink: 0;
    }

    .player-name {
        font-size: 1.05rem;
        font-weight: 800;
    }

    .player-meta {
        font-size: 0.92rem;
        opacity: 0.78;
        margin-top: 3px;
    }

    .mini-kpi {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 16px;
        padding: 12px 14px;
        background: var(--secondary-background-color);
    }

    .mini-kpi-label {
        font-size: 0.86rem;
        opacity: 0.75;
        margin-bottom: 6px;
    }

    .mini-kpi-value {
        font-size: 1.35rem;
        font-weight: 800;
    }

    .badge-gold {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 800;
        background: rgba(234, 179, 8, 0.16);
        color: #facc15;
        margin: 4px 6px 0 0;
    }

    .badge-silver {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 800;
        background: rgba(148, 163, 184, 0.15);
        color: #cbd5e1;
        margin: 4px 6px 0 0;
    }

    .badge-bronze {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 800;
        background: rgba(180, 83, 9, 0.16);
        color: #fdba74;
        margin: 4px 6px 0 0;
    }

    .insight-box {
        border-left: 4px solid rgba(59,130,246,0.7);
        padding: 10px 12px;
        border-radius: 10px;
        background: rgba(59,130,246,0.06);
        margin-top: 12px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# HELPERS
# =========================================================
def slugify(texto: str) -> str:
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    ren = {}
    for c in df.columns:
        ren[c] = slugify(c).replace("_", " ")
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


def fmt_float_br(valor, casas: int = 1) -> str:
    try:
        s = f"{float(valor):,.{casas}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,0"


def limpar_texto(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def parse_nota(valor) -> float:
    if pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    s = str(valor).strip()
    if not s:
        return 0.0

    if "," in s and "." not in s:
        s = s.replace(",", ".")
        try:
            return float(s)
        except Exception:
            return 0.0

    if "." in s and "," not in s:
        try:
            return float(s)
        except Exception:
            return 0.0

    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except Exception:
            return 0.0

    try:
        return float(s)
    except Exception:
        return 0.0


def extrair_inicio_temporada(valor: str) -> int:
    s = str(valor).strip()
    m = re.search(r"(19|20)\d{2}", s)
    if m:
        return int(m.group())
    return 0


def badge_html(texto: str, posicao: int) -> str:
    cls = "badge-bronze"
    if posicao == 1:
        cls = "badge-gold"
    elif posicao == 2:
        cls = "badge-silver"
    return f'<span class="{cls}">{texto}</span>'


def get_rank_position(df_grouped: pd.DataFrame, jogador: str, valor_col: str = "valor") -> int | None:
    if df_grouped.empty or jogador not in set(df_grouped["jogador"]):
        return None

    df_ord = df_grouped.sort_values([valor_col, "jogador"], ascending=[False, True]).reset_index(drop=True)
    df_ord["rank"] = df_ord[valor_col].rank(method="dense", ascending=False).astype(int)
    row = df_ord[df_ord["jogador"] == jogador]
    if row.empty:
        return None
    return int(row["rank"].iloc[0])


def build_rank_df(df_base: pd.DataFrame, coluna: str, titulo: str, casas: int = 0) -> pd.DataFrame:
    agg_map = {
        "jogos": ("jogos", "sum"),
        "gols": ("gols", "sum"),
        "assistencias": ("assistencias", "sum"),
        "nota": ("nota", "mean"),
        "amarelo": ("amarelo", "sum"),
        "vermelho": ("vermelho", "sum"),
    }

    base = (
        df_base.groupby("jogador", as_index=False)
        .agg(valor=agg_map[coluna])
        .sort_values(["valor", "jogador"], ascending=[False, True])
        .reset_index(drop=True)
    )
    base["posicao"] = base["valor"].rank(method="dense", ascending=False).astype(int)

    if casas > 0:
        base["valor_fmt"] = base["valor"].apply(lambda x: fmt_float_br(x, casas))
    else:
        base["valor_fmt"] = base["valor"].apply(fmt_int)

    base["titulo"] = titulo
    return base


def render_ranking(df_rank: pd.DataFrame, cor: str) -> None:
    if df_rank.empty:
        st.info("Sem dados para exibir.")
        return

    titulo = df_rank["titulo"].iloc[0]
    st.markdown(f'<div class="ranking-title" style="color:{cor};">{titulo}</div>', unsafe_allow_html=True)

    for _, row in df_rank.iterrows():
        st.markdown(f"""
            <div class="ranking-item">
                <div class="ranking-row">
                    <div class="ranking-left">
                        <div class="ranking-pos-inline">#{int(row['posicao'])}</div>
                        <div class="ranking-name">{row['jogador']}</div>
                    </div>
                    <div class="ranking-value-big">{row['valor_fmt']}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)


def get_discipline_insight(df_contexto: pd.DataFrame, jogador: str) -> str:
    disciplina = (
        df_contexto.groupby("jogador", as_index=False)
        .agg(
            jogos=("jogos", "sum"),
            amarelo=("amarelo", "sum"),
            vermelho=("vermelho", "sum"),
        )
    )

    disciplina = disciplina[disciplina["jogos"] >= 20].copy()
    if disciplina.empty or jogador not in set(disciplina["jogador"]):
        return "Não há amostra suficiente para tirar uma leitura mais forte sobre disciplina."

    disciplina["amarelos_por_100"] = (disciplina["amarelo"] / disciplina["jogos"]) * 100
    disciplina["vermelhos_por_100"] = (disciplina["vermelho"] / disciplina["jogos"]) * 100
    disciplina["indice_disciplina"] = disciplina["amarelos_por_100"] + (disciplina["vermelhos_por_100"] * 3)

    row = disciplina[disciplina["jogador"] == jogador].iloc[0]

    disciplina_baixa = disciplina.sort_values(
        ["indice_disciplina", "amarelos_por_100", "jogador"],
        ascending=[True, True, True]
    ).reset_index(drop=True)
    disciplina_baixa["rank_baixo"] = range(1, len(disciplina_baixa) + 1)

    disciplina_alta = disciplina.sort_values(
        ["indice_disciplina", "amarelos_por_100", "jogador"],
        ascending=[False, False, True]
    ).reset_index(drop=True)
    disciplina_alta["rank_alto"] = range(1, len(disciplina_alta) + 1)

    rank_baixo = int(disciplina_baixa.loc[disciplina_baixa["jogador"] == jogador, "rank_baixo"].iloc[0])
    rank_alto = int(disciplina_alta.loc[disciplina_alta["jogador"] == jogador, "rank_alto"].iloc[0])

    if row["vermelho"] == 0 and rank_baixo <= 3:
        return (
            f"Em disciplina, ele se destaca muito bem: **não recebeu cartões vermelhos** "
            f"e aparece entre os **3 jogadores mais controlados** do elenco no recorte atual."
        )

    if rank_baixo <= 5 and row["vermelho"] <= 1:
        return (
            f"O comportamento disciplinar também chama atenção: ele mantém um perfil **equilibrado**, "
            f"com baixa incidência de cartões dentro do recorte atual."
        )

    if rank_alto <= 3 and row["vermelho"] > 0:
        return (
            f"Na disciplina, o retrato é de um jogador que **atua mais no limite**: "
            f"ele aparece entre os maiores índices de advertência do elenco no recorte atual."
        )

    return (
        f"Na parte disciplinar, o jogador apresenta um perfil **intermediário**, "
        f"sem estar entre os mais punidos nem entre os mais limpos do elenco."
    )


def coletar_destaques_jogador(df_contexto: pd.DataFrame, jogador: str) -> dict:
    categorias = {
        "jogos": ("jogos", "sum", "jogos"),
        "gols": ("gols", "sum", "gols"),
        "assistencias": ("assistencias", "sum", "assistências"),
        "nota": ("nota", "mean", "nota média"),
    }

    destaques_gerais = []
    badges = []

    for _, (coluna, agg, label) in categorias.items():
        grouped = (
            df_contexto.groupby("jogador", as_index=False)
            .agg(valor=(coluna, agg))
        )

        pos = get_rank_position(grouped, jogador)
        if pos is not None and pos <= 3:
            valor_jog = grouped.loc[grouped["jogador"] == jogador, "valor"].iloc[0]
            destaques_gerais.append({
                "label": label,
                "posicao": pos,
                "valor": valor_jog,
            })
            badges.append(badge_html(f"Top {pos} em {label}", pos))

    destaques_comp = []

    for competicao in sorted(df_contexto["competicao"].dropna().astype(str).unique().tolist()):
        df_comp = df_contexto[df_contexto["competicao"] == competicao].copy()

        for _, (coluna, agg, label) in categorias.items():
            grouped = (
                df_comp.groupby("jogador", as_index=False)
                .agg(valor=(coluna, agg))
            )

            pos = get_rank_position(grouped, jogador)
            if pos is not None and pos <= 3:
                valor_jog = grouped.loc[grouped["jogador"] == jogador, "valor"].iloc[0]
                destaques_comp.append({
                    "competicao": competicao,
                    "label": label,
                    "posicao": pos,
                    "valor": valor_jog,
                })

    destaques_comp = sorted(
        destaques_comp,
        key=lambda x: (x["posicao"], x["competicao"], x["label"])
    )

    return {
        "gerais": destaques_gerais,
        "competicao": destaques_comp,
        "badges": badges,
    }


def gerar_texto_jogador(df_jogador: pd.DataFrame, df_contexto: pd.DataFrame, jogador: str) -> tuple[str, str, str]:
    temporadas = sorted(
        df_jogador["temporada"].dropna().astype(str).unique().tolist(),
        key=extrair_inicio_temporada
    )
    competicoes = sorted(df_jogador["competicao"].dropna().astype(str).unique().tolist())

    total_temporadas = len(temporadas)
    total_competicoes = len(competicoes)
    jogos = int(df_jogador["jogos"].sum())
    gols = int(df_jogador["gols"].sum())
    assist = int(df_jogador["assistencias"].sum())
    amarelos = int(df_jogador["amarelo"].sum())
    vermelhos = int(df_jogador["vermelho"].sum())
    nota_media = round(df_jogador["nota"].mean(), 2) if len(df_jogador) else 0.0

    melhor_temp = (
        df_jogador.groupby("temporada", as_index=False)
        .agg(
            jogos=("jogos", "sum"),
            gols=("gols", "sum"),
            assistencias=("assistencias", "sum"),
            nota=("nota", "mean"),
        )
        .assign(ordem=lambda x: x["temporada"].apply(extrair_inicio_temporada))
        .sort_values(["gols", "assistencias", "nota", "jogos", "ordem"], ascending=False)
        .head(1)
    )

    if not melhor_temp.empty:
        mt = melhor_temp.iloc[0]
        texto_temp = (
            f"A temporada de maior destaque foi **{mt['temporada']}**, "
            f"com **{int(mt['jogos'])} jogos**, **{int(mt['gols'])} gols**, "
            f"**{int(mt['assistencias'])} assistências** e **nota média {fmt_float_br(mt['nota'], 2)}**."
        )
    else:
        texto_temp = "Não foi possível identificar uma temporada de maior destaque."

    destaques = coletar_destaques_jogador(df_contexto, jogador)

    frases_destaque = []
    gerais_ordenados = sorted(destaques["gerais"], key=lambda x: (x["posicao"], x["label"]))

    for item in gerais_ordenados[:3]:
        if item["posicao"] == 1:
            frases_destaque.append(
                f"Hoje ele é o **recordista do clube** no recorte atual em **{item['label']}**, ocupando o **1º lugar geral**."
            )
        else:
            frases_destaque.append(
                f"Ele também aparece no **top {item['posicao']} geral** do clube em **{item['label']}**."
            )

    comp_ordenados = sorted(destaques["competicao"], key=lambda x: (x["posicao"], x["competicao"], x["label"]))
    usados = set()
    frases_comp = []

    for item in comp_ordenados:
        chave = (item["competicao"], item["label"])
        if chave in usados:
            continue
        usados.add(chave)

        if item["posicao"] == 1:
            frases_comp.append(
                f"Na **{item['competicao']}**, ele é o **recordista do clube em {item['label']}** dentro do recorte atual."
            )
        else:
            frases_comp.append(
                f"Na **{item['competicao']}**, ele também aparece no **top {item['posicao']} do clube em {item['label']}**."
            )

        if len(frases_comp) >= 3:
            break

    bloco_destaque = " ".join(frases_destaque + frases_comp)
    if not bloco_destaque:
        bloco_destaque = (
            "No recorte atual, ele não aparece entre os três primeiros do clube nas categorias ofensivas e de participação, "
            "mas ainda assim oferece contribuição relevante dentro do conjunto filtrado."
        )

    disciplina_texto = get_discipline_insight(df_contexto, jogador)

    texto_principal = (
        f"**{jogador}** tem registro em **{total_temporadas} temporada(s)** no clube, "
        f"distribuído em **{total_competicoes} competição(ões)**. "
        f"No total, soma **{jogos} jogos**, **{gols} gols** e **{assist} assistências**, "
        f"com **nota média geral de {fmt_float_br(nota_media, 2)}**. "
        f"Além disso, recebeu **{amarelos} cartão(ões) amarelo(s)** e **{vermelhos} vermelho(s)**. "
        f"{texto_temp} {bloco_destaque}"
    )

    badges_html = "".join(destaques["badges"][:6])

    return texto_principal, badges_html, disciplina_texto


def construir_tabela_lideres_temporada(df_contexto: pd.DataFrame, metrica: str) -> pd.DataFrame:
    mapa = {
        "Gols": "gols",
        "Assistências": "assistencias",
        "Jogos": "jogos",
    }
    col = mapa[metrica]

    base = (
        df_contexto.groupby(["temporada", "jogador"], as_index=False)
        .agg(valor_temporada=(col, "sum"))
    )
    base["ordem"] = base["temporada"].apply(extrair_inicio_temporada)
    base = base.sort_values(["ordem", "temporada"])

    base["valor_acumulado"] = base.groupby("jogador")["valor_temporada"].cumsum()

    lideres = []
    for temporada in base["temporada"].drop_duplicates().tolist():
        snap = base[base["temporada"] == temporada].copy()
        snap = snap.sort_values(["valor_acumulado", "jogador"], ascending=[False, True])
        topo = snap.iloc[0]
        lideres.append({
            "Temporada": temporada,
            "Líder histórico": topo["jogador"],
            f"{metrica} acumulados": int(topo["valor_acumulado"]),
        })

    return pd.DataFrame(lideres)


def construir_marcos_historicos(df_contexto: pd.DataFrame, metrica: str) -> pd.DataFrame:
    mapa = {
        "Gols": "gols",
        "Assistências": "assistencias",
        "Jogos": "jogos",
    }
    col = mapa[metrica]

    base = (
        df_contexto.groupby(["temporada", "jogador"], as_index=False)
        .agg(valor_temporada=(col, "sum"))
    )
    base["ordem"] = base["temporada"].apply(extrair_inicio_temporada)
    base = base.sort_values(["ordem", "temporada"])

    base["valor_acumulado"] = base.groupby("jogador")["valor_temporada"].cumsum()

    lider_corrente = None
    marcos = []

    for temporada in base["temporada"].drop_duplicates().tolist():
        snap = base[base["temporada"] == temporada].copy()
        snap = snap.sort_values(["valor_acumulado", "jogador"], ascending=[False, True])
        topo = snap.iloc[0]["jogador"]
        valor = int(snap.iloc[0]["valor_acumulado"])

        if topo != lider_corrente:
            marcos.append({
                "Temporada": temporada,
                "Novo líder histórico": topo,
                f"{metrica} acumulados": valor,
            })
            lider_corrente = topo

    return pd.DataFrame(marcos)


# =========================================================
# CARGA DOS DADOS - GOOGLE SHEETS
# =========================================================
@st.cache_data(ttl=60, show_spinner="Carregando estatísticas do Google Sheets...")
def carregar_estatisticas() -> tuple[pd.DataFrame, dict[str, str]]:
    try:
        df = pd.read_csv(URL_STATS)
    except Exception as e:
        raise RuntimeError(f"Erro ao carregar a aba Estatística de jogadores do Google Sheets: {e}")

    if df.empty:
        raise RuntimeError("A aba Estatística de jogadores veio vazia do Google Sheets.")

    df = normalizar_colunas(df)

    cols = {
        "temporada": achar_coluna(df, ["temporada"]),
        "competicao": achar_coluna(df, ["competicao", "competição"]),
        "jogador": achar_coluna(df, ["jogador", "player"]),
        "jogos": achar_coluna(df, ["jogos"]),
        "gols": achar_coluna(df, ["gols"]),
        "assistencias": achar_coluna(df, ["assistencias", "assistências"]),
        "nota": achar_coluna(df, ["nota", "media", "média"]),
        "amarelo": achar_coluna(df, ["amarelo", "amarelos"]),
        "vermelho": achar_coluna(df, ["vermelho", "vermelhos"]),
    }

    df = df.rename(columns={
        cols["temporada"]: "temporada",
        cols["competicao"]: "competicao",
        cols["jogador"]: "jogador",
        cols["jogos"]: "jogos",
        cols["gols"]: "gols",
        cols["assistencias"]: "assistencias",
        cols["nota"]: "nota",
        cols["amarelo"]: "amarelo",
        cols["vermelho"]: "vermelho",
    }).copy()

    for col in ["jogos", "gols", "assistencias", "amarelo", "vermelho"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df["nota"] = df["nota"].apply(parse_nota)

    df["temporada"] = df["temporada"].astype(str).str.strip()
    df["competicao"] = df["competicao"].astype(str).str.strip()
    df["jogador"] = df["jogador"].astype(str).str.strip()
    df["ordem_temporada"] = df["temporada"].apply(extrair_inicio_temporada)

    df = df[df["jogador"] != ""].copy()

    return df, cols


try:
    df, cols = carregar_estatisticas()
except Exception as e:
    st.error(str(e))
    st.stop()

# =========================================================
# TOPO
# =========================================================
st.markdown("""
<div class="hero">
    <h1>📊 Estatística de Jogadores</h1>
    <p>Filtros completos, rankings por categoria, análise individual e linha do tempo comparativa.</p>
</div>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Filtros")

temporadas = sorted(df["temporada"].dropna().unique().tolist(), key=extrair_inicio_temporada)
competicoes = sorted(df["competicao"].dropna().unique().tolist())
jogadores = sorted(df["jogador"].dropna().unique().tolist())

temp_sel = st.sidebar.multiselect("Temporada", temporadas)
comp_sel = st.sidebar.multiselect("Competição", competicoes)
jog_sel = st.sidebar.multiselect("Jogador", jogadores)

st.sidebar.markdown("**Filtros numéricos**")

jogos_min, jogos_max = int(df["jogos"].min()), int(df["jogos"].max())
gols_min, gols_max = int(df["gols"].min()), int(df["gols"].max())
assist_min, assist_max = int(df["assistencias"].min()), int(df["assistencias"].max())
nota_min, nota_max = float(df["nota"].min()), float(df["nota"].max())
am_min, am_max = int(df["amarelo"].min()), int(df["amarelo"].max())
vm_min, vm_max = int(df["vermelho"].min()), int(df["vermelho"].max())

faixa_jogos = st.sidebar.slider("Jogos", jogos_min, jogos_max, (jogos_min, jogos_max))
faixa_gols = st.sidebar.slider("Gols", gols_min, gols_max, (gols_min, gols_max))
faixa_assist = st.sidebar.slider("Assistências", assist_min, assist_max, (assist_min, assist_max))
faixa_nota = st.sidebar.slider("Nota", float(nota_min), float(nota_max), (float(nota_min), float(nota_max)), step=0.1)
faixa_am = st.sidebar.slider("Amarelos", am_min, am_max, (am_min, am_max))
faixa_vm = st.sidebar.slider("Vermelhos", vm_min, vm_max, (vm_min, vm_max))

# =========================================================
# FILTROS
# =========================================================
# contexto_rank = tudo que deve valer para ranking geral daquela página,
# sem restringir pelo filtro de jogador
contexto_rank = df.copy()

if temp_sel:
    contexto_rank = contexto_rank[contexto_rank["temporada"].isin(temp_sel)]

if comp_sel:
    contexto_rank = contexto_rank[contexto_rank["competicao"].isin(comp_sel)]

contexto_rank = contexto_rank[
    (contexto_rank["jogos"].between(faixa_jogos[0], faixa_jogos[1])) &
    (contexto_rank["gols"].between(faixa_gols[0], faixa_gols[1])) &
    (contexto_rank["assistencias"].between(faixa_assist[0], faixa_assist[1])) &
    (contexto_rank["nota"].between(faixa_nota[0], faixa_nota[1])) &
    (contexto_rank["amarelo"].between(faixa_am[0], faixa_am[1])) &
    (contexto_rank["vermelho"].between(faixa_vm[0], faixa_vm[1]))
]

filtrado = contexto_rank.copy()

if jog_sel:
    filtrado = filtrado[filtrado["jogador"].isin(jog_sel)]

if filtrado.empty:
    st.warning("Nenhum registro encontrado com os filtros atuais.")
    st.stop()

# =========================================================
# KPIS
# =========================================================
total_registros = len(filtrado)
total_jogadores = filtrado["jogador"].nunique()
total_temporadas = filtrado["temporada"].nunique()
total_jogos = int(filtrado["jogos"].sum())
total_gols = int(filtrado["gols"].sum())
total_assist = int(filtrado["assistencias"].sum())
nota_media = filtrado["nota"].mean()

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
kpis = [
    ("Registros", fmt_int(total_registros)),
    ("Jogadores", fmt_int(total_jogadores)),
    ("Temporadas", fmt_int(total_temporadas)),
    ("Jogos", fmt_int(total_jogos)),
    ("Gols", fmt_int(total_gols)),
    ("Assistências", fmt_int(total_assist)),
    ("Nota média", fmt_float_br(nota_media, 2)),
]

for col, (label, value) in zip([k1, k2, k3, k4, k5, k6, k7], kpis):
    with col:
        st.markdown(f"""
        <div class="kpi">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# ABAS
# =========================================================
aba1, aba2, aba3 = st.tabs([
    "📋 Visão geral",
    "👤 Análise individual",
    "📈 Linha do tempo & comparação"
])

# =========================================================
# ABA 1 - VISÃO GERAL
# =========================================================
with aba1:
    st.markdown("<br>", unsafe_allow_html=True)

    resumo_jogadores = (
        filtrado.groupby("jogador", as_index=False)
        .agg(
            temporadas=("temporada", "nunique"),
            competicoes=("competicao", "nunique"),
            jogos=("jogos", "sum"),
            gols=("gols", "sum"),
            assistencias=("assistencias", "sum"),
            nota=("nota", "mean"),
            amarelo=("amarelo", "sum"),
            vermelho=("vermelho", "sum"),
        )
        .sort_values(["gols", "assistencias", "jogos"], ascending=False)
    )

    rank_gols = build_rank_df(contexto_rank, "gols", "TOP DE GOLS", 0)
    rank_assist = build_rank_df(contexto_rank, "assistencias", "TOP DE ASSISTÊNCIAS", 0)
    rank_jogos = build_rank_df(contexto_rank, "jogos", "TOP DE JOGOS", 0)
    rank_nota = build_rank_df(contexto_rank, "nota", "TOP DE NOTAS", 2)
    rank_amarelo = build_rank_df(contexto_rank, "amarelo", "TOP DE AMARELOS", 0)
    rank_vermelho = build_rank_df(contexto_rank, "vermelho", "TOP DE VERMELHOS", 0)

    if jog_sel:
        rank_gols_show = rank_gols[rank_gols["jogador"].isin(jog_sel)].sort_values(["posicao", "jogador"]).head(5)
        rank_assist_show = rank_assist[rank_assist["jogador"].isin(jog_sel)].sort_values(["posicao", "jogador"]).head(5)
        rank_jogos_show = rank_jogos[rank_jogos["jogador"].isin(jog_sel)].sort_values(["posicao", "jogador"]).head(5)
        rank_nota_show = rank_nota[rank_nota["jogador"].isin(jog_sel)].sort_values(["posicao", "jogador"]).head(5)
        rank_amarelo_show = rank_amarelo[rank_amarelo["jogador"].isin(jog_sel)].sort_values(["posicao", "jogador"]).head(5)
        rank_vermelho_show = rank_vermelho[rank_vermelho["jogador"].isin(jog_sel)].sort_values(["posicao", "jogador"]).head(5)
    else:
        rank_gols_show = rank_gols.head(5)
        rank_assist_show = rank_assist.head(5)
        rank_jogos_show = rank_jogos.head(5)
        rank_nota_show = rank_nota.head(5)
        rank_amarelo_show = rank_amarelo.head(5)
        rank_vermelho_show = rank_vermelho.head(5)

    # Nova ordem pedida
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    row2_c1, row2_c2, row2_c3 = st.columns(3)

    with row1_c1:
        render_ranking(rank_gols_show, "#22c55e")
    with row1_c2:
        render_ranking(rank_assist_show, "#14b8a6")
    with row1_c3:
        render_ranking(rank_jogos_show, "#60a5fa")

    with row2_c1:
        render_ranking(rank_nota_show, "#f59e0b")
    with row2_c2:
        render_ranking(rank_amarelo_show, "#eab308")
    with row2_c3:
        render_ranking(rank_vermelho_show, "#ef4444")

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Tabela consolidada por jogador")

    tabela = resumo_jogadores.copy()
    tabela["nota"] = tabela["nota"].round(2)

    tabela = tabela.rename(columns={
        "jogador": "Jogador",
        "temporadas": "Temporadas",
        "competicoes": "Competições",
        "jogos": "Jogos",
        "gols": "Gols",
        "assistencias": "Assistências",
        "nota": "Nota média",
        "amarelo": "Amarelos",
        "vermelho": "Vermelhos",
    })

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True,
        height=520
    )

# =========================================================
# ABA 2 - ANÁLISE INDIVIDUAL
# =========================================================
with aba2:
    st.markdown("<br>", unsafe_allow_html=True)

    jogadores_disponiveis = sorted(filtrado["jogador"].dropna().unique().tolist())
    jogador_escolhido = st.selectbox("Escolha um jogador", jogadores_disponiveis)

    df_jogador = filtrado[filtrado["jogador"] == jogador_escolhido].copy()

    if df_jogador.empty:
        st.info("Nenhum dado encontrado para esse jogador no recorte atual.")
    else:
        texto, badges_html, disciplina_texto = gerar_texto_jogador(df_jogador, contexto_rank, jogador_escolhido)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader(jogador_escolhido)
        if badges_html:
            st.markdown(badges_html, unsafe_allow_html=True)
        st.write(texto)
        st.markdown(f'<div class="insight-box">{disciplina_texto}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        total_jogos_j = int(df_jogador["jogos"].sum())
        total_gols_j = int(df_jogador["gols"].sum())
        total_assist_j = int(df_jogador["assistencias"].sum())
        nota_media_j = df_jogador["nota"].mean()
        amarelos_j = int(df_jogador["amarelo"].sum())
        vermelhos_j = int(df_jogador["vermelho"].sum())

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        mini = [
            ("Jogos", fmt_int(total_jogos_j)),
            ("Gols", fmt_int(total_gols_j)),
            ("Assist.", fmt_int(total_assist_j)),
            ("Nota", fmt_float_br(nota_media_j, 2)),
            ("Amarelos", fmt_int(amarelos_j)),
            ("Vermelhos", fmt_int(vermelhos_j)),
        ]

        for col, (label, value) in zip([m1, m2, m3, m4, m5, m6], mini):
            with col:
                st.markdown(f"""
                <div class="mini-kpi">
                    <div class="mini-kpi-label">{label}</div>
                    <div class="mini-kpi-value">{value}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        por_temporada = (
            df_jogador.groupby("temporada", as_index=False)
            .agg(
                jogos=("jogos", "sum"),
                gols=("gols", "sum"),
                assistencias=("assistencias", "sum"),
                nota=("nota", "mean"),
                amarelo=("amarelo", "sum"),
                vermelho=("vermelho", "sum"),
            )
        )
        por_temporada["ordem"] = por_temporada["temporada"].apply(extrair_inicio_temporada)
        por_temporada = por_temporada.sort_values(["ordem", "temporada"])

        por_competicao = (
            df_jogador.groupby("competicao", as_index=False)
            .agg(
                jogos=("jogos", "sum"),
                gols=("gols", "sum"),
                assistencias=("assistencias", "sum"),
                nota=("nota", "mean"),
                amarelo=("amarelo", "sum"),
                vermelho=("vermelho", "sum"),
            )
            .sort_values(["gols", "assistencias", "jogos"], ascending=False)
        )

        g1, g2 = st.columns(2)

        with g1:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("**Desempenho por temporada**")
            st.bar_chart(
                por_temporada.set_index("temporada")[["jogos", "gols", "assistencias"]],
                use_container_width=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with g2:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("**Notas por temporada**")
            st.line_chart(
                por_temporada.set_index("temporada")[["nota"]],
                use_container_width=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        g3, g4 = st.columns(2)

        with g3:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("**Distribuição por competição**")
            st.bar_chart(
                por_competicao.set_index("competicao")[["jogos", "gols", "assistencias"]],
                use_container_width=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with g4:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("**Disciplina por temporada**")
            st.bar_chart(
                por_temporada.set_index("temporada")[["amarelo", "vermelho"]],
                use_container_width=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("Tabela do jogador")
        tabela_j = por_temporada.copy()
        tabela_j["nota"] = tabela_j["nota"].round(2)
        tabela_j = tabela_j.rename(columns={
            "temporada": "Temporada",
            "jogos": "Jogos",
            "gols": "Gols",
            "assistencias": "Assistências",
            "nota": "Nota média",
            "amarelo": "Amarelos",
            "vermelho": "Vermelhos",
        })

        st.dataframe(
            tabela_j[["Temporada", "Jogos", "Gols", "Assistências", "Nota média", "Amarelos", "Vermelhos"]],
            use_container_width=True,
            hide_index=True,
            height=320
        )

# =========================================================
# ABA 3 - LINHA DO TEMPO & COMPARAÇÃO
# =========================================================
with aba3:
    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("Comparação por temporada")

    jogadores_comparacao = sorted(contexto_rank["jogador"].dropna().unique().tolist())
    default_compare = jogadores_comparacao[:2] if len(jogadores_comparacao) >= 2 else jogadores_comparacao

    jogadores_sel_comp = st.multiselect(
        "Escolha até 4 jogadores para comparar",
        options=jogadores_comparacao,
        default=default_compare[:2],
        max_selections=4
    )

    metrica_comp = st.selectbox(
        "Métrica da comparação",
        ["Gols", "Assistências", "Jogos", "Nota"]
    )

    tipo_serie = st.radio(
        "Tipo de série",
        ["Por temporada", "Acumulado"],
        horizontal=True
    )

    mapa_metricas = {
        "Gols": ("gols", "sum"),
        "Assistências": ("assistencias", "sum"),
        "Jogos": ("jogos", "sum"),
        "Nota": ("nota", "mean"),
    }

    if jogadores_sel_comp:
        col_metrica, agg_metrica = mapa_metricas[metrica_comp]

        base_comp = contexto_rank[contexto_rank["jogador"].isin(jogadores_sel_comp)].copy()

        serie = (
            base_comp.groupby(["temporada", "jogador"], as_index=False)
            .agg(valor=(col_metrica, agg_metrica))
        )
        serie["ordem"] = serie["temporada"].apply(extrair_inicio_temporada)
        serie = serie.sort_values(["ordem", "temporada", "jogador"])

        tabela_plot = (
            serie.pivot(index="temporada", columns="jogador", values="valor")
            .sort_index(key=lambda idx: [extrair_inicio_temporada(x) for x in idx])
            .fillna(0)
        )

        if tipo_serie == "Acumulado" and metrica_comp != "Nota":
            tabela_plot = tabela_plot.cumsum()

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(f"**Comparação de {metrica_comp.lower()}**")
        st.line_chart(tabela_plot, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        tabela_compare = tabela_plot.reset_index()
        st.dataframe(tabela_compare, use_container_width=True, hide_index=True)
    else:
        st.info("Selecione ao menos um jogador para comparar.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Linha do tempo dos líderes históricos")

    metrica_linha = st.selectbox(
        "Escolha a métrica histórica",
        ["Gols", "Assistências", "Jogos"]
    )

    lideres_temp = construir_tabela_lideres_temporada(contexto_rank, metrica_linha)
    marcos_hist = construir_marcos_historicos(contexto_rank, metrica_linha)

    c_hist1, c_hist2 = st.columns(2)

    with c_hist1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("**Quem terminou cada temporada como líder histórico**")
        if lideres_temp.empty:
            st.info("Sem dados suficientes.")
        else:
            st.dataframe(lideres_temp, use_container_width=True, hide_index=True, height=340)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_hist2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("**Mudanças de liderança histórica**")
        if marcos_hist.empty:
            st.info("Sem mudanças de liderança identificadas.")
        else:
            st.dataframe(marcos_hist, use_container_width=True, hide_index=True, height=340)
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "Como a base está agregada por temporada, os marcos históricos são identificados ao fim de cada temporada, "
        "não jogo a jogo."
    )