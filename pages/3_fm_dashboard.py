from __future__ import annotations

from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
from io import StringIO

import pandas as pd
import requests
import streamlit as st

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="FM Dashboard", page_icon="⚽", layout="wide")

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

URL_JOGOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQstFkeNnP5dKUnfHjl2UScwn2UnIHUuGuHqx0pJMlo86ovTeqMB6wZ3MvrGGwGPkxkWzRbdPFUV90y/pub?gid=182820443&single=true&output=csv"

ASSETS_DIR = DATA_DIR / "assets" / "clubes"

SPORTSDB_API_KEY = "123"
SPORTSDB_BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{SPORTSDB_API_KEY}"

TEAM_NAME_ALIASES = {}

TEAM_BADGE_OVERRIDES = {}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

# =========================================================
# CSS
# =========================================================
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1380px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    .small-muted {
        font-size: 0.92rem;
        opacity: 0.72;
    }

    .kpi {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 18px;
        padding: 14px 16px;
        background: var(--secondary-background-color);
        min-height: 108px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .kpi-label {
        font-size: 0.95rem;
        opacity: 0.75;
        margin-bottom: 8px;
    }

    .kpi-value {
        font-size: 2.1rem;
        font-weight: 800;
        line-height: 1.05;
        color: var(--text-color);
    }

    .card-box {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 18px;
        padding: 16px;
        background: var(--secondary-background-color);
    }

    .result-tag {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 0.83rem;
        font-weight: 700;
        margin-top: 6px;
    }

    .tag-v {
        background: rgba(34, 197, 94, 0.15);
        color: rgb(22, 101, 52);
    }

    .tag-e {
        background: rgba(234, 179, 8, 0.18);
        color: rgb(146, 64, 14);
    }

    .tag-d {
        background: rgba(239, 68, 68, 0.15);
        color: rgb(153, 27, 27);
    }

    .form-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 4px;
    }

    .form-dot {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        display: inline-block;
        border: 2px solid rgba(120,120,120,0.45);
        cursor: help;
    }

    .score-big {
        font-size: 2.25rem;
        font-weight: 800;
        text-align: right;
        white-space: nowrap;
        color: var(--text-color);
        margin-right: 8px;
    }

    .score-mid {
        font-size: 1.45rem;
        font-weight: 800;
        text-align: right;
        white-space: nowrap;
        color: var(--text-color);
        margin-right: 8px;
    }

    .section-title {
        font-size: 1.2rem;
        font-weight: 800;
        margin-bottom: 2px;
    }

    .club-name {
        font-size: 1.08rem;
        font-weight: 800;
        line-height: 1.2;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================
def slugify(texto: str) -> str:
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


def fmt_int(valor: int | float) -> str:
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return "0"


def fmt_float(valor: float, casas: int = 2) -> str:
    try:
        s = f"{float(valor):,.{casas}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    ren = {}
    for c in df.columns:
        ren[c] = slugify(c).replace("_", " ")
    return df.rename(columns=ren)


def achar_coluna(df: pd.DataFrame, opcoes: list[str]) -> str:
    for op in opcoes:
        if op in df.columns:
            return op
    raise KeyError(f"Coluna não encontrada: {opcoes}")


def percentual(valor: float, total: float) -> float:
    return round((valor / total) * 100, 1) if total else 0.0


def classe_resultado(r: str) -> tuple[str, str]:
    r = str(r).strip().lower().replace("vitória", "vitoria")
    if r == "vitoria":
        return "Vitória", "tag-v"
    if r == "empate":
        return "Empate", "tag-e"
    return "Derrota", "tag-d"


def normalizar_nome_time(nome: str) -> str:
    nome_limpo = str(nome).strip()
    if not nome_limpo:
        return nome_limpo

    if nome_limpo in TEAM_NAME_ALIASES:
        return TEAM_NAME_ALIASES[nome_limpo]

    slug = slugify(nome_limpo)
    for chave, valor in TEAM_NAME_ALIASES.items():
        if slugify(chave) == slug:
            return valor

    return nome_limpo


def pontuacao_nome(alvo: str, candidato: str) -> int:
    alvo_slug = slugify(alvo)
    cand_slug = slugify(candidato)

    if not cand_slug:
        return 0
    if alvo_slug == cand_slug:
        return 100
    if alvo_slug in cand_slug or cand_slug in alvo_slug:
        return 70

    alvo_tokens = set(alvo_slug.split("_"))
    cand_tokens = set(cand_slug.split("_"))
    inter = len(alvo_tokens & cand_tokens)
    if inter == 0:
        return 0
    return inter * 10


def normalizar_local(valor: str) -> str:
    v = slugify(valor).replace("_", " ")
    mapa = {
        "casa": "Casa",
        "fora": "Fora",
        "neutro": "Neutro",
        "mandante": "Casa",
        "visitante": "Fora",
        "home": "Casa",
        "away": "Fora",
        "neutral": "Neutro",
    }
    return mapa.get(v, str(valor).strip().title())


@st.cache_data
def listar_escudos_locais() -> dict[str, Path]:
    mapa: dict[str, Path] = {}
    if not ASSETS_DIR.exists():
        return mapa

    for arq in ASSETS_DIR.iterdir():
        if arq.is_file() and arq.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            mapa[arq.stem.lower()] = arq.resolve()

    return mapa


def encontrar_escudo_local(nome: str) -> Path | None:
    mapa = listar_escudos_locais()
    slug = slugify(nome)

    if slug in mapa:
        return mapa[slug]

    variantes = {
        slug,
        slug.replace("_fc", ""),
        slug.replace("_cf", ""),
        slug.replace("_club", ""),
    }

    for stem, path in mapa.items():
        if stem in variantes or slug in stem or stem in slug:
            return path

    return None


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def buscar_escudo_online(nome_time: str) -> str | None:
    nome_original = str(nome_time).strip()
    if not nome_original:
        return None

    if nome_original in TEAM_BADGE_OVERRIDES:
        return TEAM_BADGE_OVERRIDES[nome_original]

    nome_busca = normalizar_nome_time(nome_original)

    try:
        url = f"{SPORTSDB_BASE_URL}/searchteams.php?t={quote(nome_busca)}"
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        resp.raise_for_status()
        data = resp.json()

        teams = data.get("teams") or []
        if not teams:
            return None

        melhor_time = None
        melhor_score = -1

        for team in teams:
            nomes_candidatos = [
                team.get("strTeam", ""),
                team.get("strTeamShort", ""),
                team.get("strAlternate", ""),
            ]
            score = max((pontuacao_nome(nome_busca, n) for n in nomes_candidatos if n), default=0)
            if score > melhor_score:
                melhor_score = score
                melhor_time = team

        if not melhor_time:
            return None

        badge = (
            melhor_time.get("strBadge")
            or melhor_time.get("strLogo")
            or melhor_time.get("strTeamBadge")
        )

        if badge and isinstance(badge, str) and badge.startswith("http"):
            return badge

        return None

    except Exception:
        return None


def obter_escudo(nome: str) -> str | Path | None:
    local = encontrar_escudo_local(nome)
    if local and local.exists():
        return local

    online = buscar_escudo_online(nome)
    if online:
        return online

    return None


def render_logo(nome: str, largura: int = 44) -> None:
    escudo = obter_escudo(nome)
    if escudo:
        st.image(str(escudo), width=largura)
    else:
        st.markdown(
            f"""
            <div style="
                width:{largura}px;
                height:{largura}px;
                display:flex;
                align-items:center;
                justify-content:center;
                border-radius:12px;
                border:1px solid rgba(128,128,128,0.18);
                background:var(--secondary-background-color);
                font-size:1.1rem;
            ">🛡️</div>
            """,
            unsafe_allow_html=True,
        )


def render_result_tag(resultado_norm: str) -> None:
    nome_res, classe = classe_resultado(resultado_norm)
    st.markdown(
        f'<span class="result-tag {classe}">{nome_res}</span>',
        unsafe_allow_html=True,
    )


def resumo_campanha_str(vitorias: int, empates: int, derrotas: int) -> str:
    return f"{int(vitorias)}V {int(empates)}E {int(derrotas)}D"


@st.cache_data(show_spinner=False)
def gerar_relatorio_escudos_faltando(times: tuple[str, ...]) -> pd.DataFrame:
    registros = []
    for clube in times:
        escudo_local = encontrar_escudo_local(clube)
        escudo_online = buscar_escudo_online(clube)

        if not escudo_local and not escudo_online:
            registros.append(
                {
                    "clube": clube,
                    "slug_sugerido_arquivo": slugify(clube),
                    "arquivo_local_esperado": str(ASSETS_DIR / f"{slugify(clube)}.png"),
                }
            )

    return pd.DataFrame(registros)


# =========================================================
# DADOS - GOOGLE SHEETS PUBLICADO COMO CSV
# =========================================================
@st.cache_data(ttl=60, show_spinner="Carregando dados do Google Sheets...")
def carregar() -> tuple[pd.DataFrame, dict[str, str]]:
    try:
        df = pd.read_csv(URL_JOGOS)
    except Exception as e:
        raise RuntimeError(f"Erro ao carregar a aba Jogos do Google Sheets: {e}")

    if df.empty:
        raise RuntimeError("A aba Jogos veio vazia do Google Sheets.")

    df = normalizar_colunas(df)

    cols = {
        "temporada": achar_coluna(df, ["temporada"]),
        "competicao": achar_coluna(df, ["competicao", "competição"]),
        "adversario": achar_coluna(df, ["adversario", "adversário"]),
        "resultado": achar_coluna(df, ["resultado"]),
        "gols_pro": achar_coluna(df, ["gols pro", "gols pró"]),
        "gols_contra": achar_coluna(df, ["gols contra"]),
        "local": achar_coluna(df, ["local", "mando de campo"]),
    }

    df = df.copy()

    df[cols["gols_pro"]] = pd.to_numeric(df[cols["gols_pro"]], errors="coerce").fillna(0).astype(int)
    df[cols["gols_contra"]] = pd.to_numeric(df[cols["gols_contra"]], errors="coerce").fillna(0).astype(int)
    df[cols["local"]] = df[cols["local"]].astype(str).apply(normalizar_local)

    df["resultado_norm"] = (
        df[cols["resultado"]]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace("vitória", "vitoria", regex=False)
    )

    df["saldo"] = df[cols["gols_pro"]] - df[cols["gols_contra"]]
    df["pontos"] = df["resultado_norm"].map({"vitoria": 3, "empate": 1, "derrota": 0}).fillna(0).astype(int)

    return df, cols


try:
    df, cols = carregar()
except Exception as e:
    st.error(str(e))
    st.stop()

# =========================================================
# SESSION STATE
# =========================================================
if "time_selecionado" not in st.session_state:
    st.session_state.time_selecionado = None

if "competicoes_ativas" not in st.session_state:
    st.session_state.competicoes_ativas = sorted(df[cols["competicao"]].dropna().unique().tolist())

# =========================================================
# SIDEBAR / FILTROS
# =========================================================
st.sidebar.header("Filtros")

temporadas = sorted(df[cols["temporada"]].dropna().unique().tolist())
competicoes = sorted(df[cols["competicao"]].dropna().unique().tolist())
adversarios = sorted(df[cols["adversario"]].dropna().unique().tolist())
mandos = ["Todas", "Casa", "Fora", "Neutro"]

temporadas_opcoes = ["Todas"] + temporadas
sel_temp = st.sidebar.selectbox(
    "Temporada",
    temporadas_opcoes,
    index=len(temporadas_opcoes) - 1 if len(temporadas_opcoes) > 1 else 0,
)

st.sidebar.markdown("**Competições**")

col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("Selecionar todas", use_container_width=True):
        st.session_state.competicoes_ativas = competicoes.copy()
with col_btn2:
    if st.button("Limpar", use_container_width=True):
        st.session_state.competicoes_ativas = []

if hasattr(st.sidebar, "pills"):
    comp_sel = st.sidebar.pills(
        "Selecione as competições",
        options=competicoes,
        default=st.session_state.competicoes_ativas if st.session_state.competicoes_ativas else [],
        selection_mode="multi",
        label_visibility="collapsed",
    )
    st.session_state.competicoes_ativas = comp_sel if comp_sel else []
else:
    comp_sel = st.sidebar.multiselect(
        "Selecione as competições",
        options=competicoes,
        default=st.session_state.competicoes_ativas,
        label_visibility="collapsed",
    )
    st.session_state.competicoes_ativas = comp_sel

sel_mando = st.sidebar.radio("Mando de campo", mandos, index=0)
sel_adv = st.sidebar.multiselect("Adversário", adversarios)
qtd_jogos = st.sidebar.slider("Quantidade de jogos exibidos", 5, 30, 10, 5)
qtd_confrontos = st.sidebar.slider("Quantidade de adversários exibidos", 3, 18, 6, 3)
mostrar_diag = st.sidebar.checkbox("Diagnóstico de escudos")

filtrado = df.copy()

if sel_temp != "Todas":
    filtrado = filtrado[filtrado[cols["temporada"]] == sel_temp]

if st.session_state.competicoes_ativas:
    filtrado = filtrado[filtrado[cols["competicao"]].isin(st.session_state.competicoes_ativas)]

if sel_mando != "Todas":
    filtrado = filtrado[filtrado[cols["local"]] == sel_mando]

if sel_adv:
    filtrado = filtrado[filtrado[cols["adversario"]].isin(sel_adv)]

if filtrado.empty:
    st.warning("Nenhum jogo encontrado com esses filtros.")
    st.stop()

# =========================================================
# TOPO
# =========================================================
st.title("FM Dashboard")
st.caption("Dados carregados diretamente do Google Sheets publicado como CSV.")

total = len(filtrado)
vit = int((filtrado["resultado_norm"] == "vitoria").sum())
emp = int((filtrado["resultado_norm"] == "empate").sum())
der = int((filtrado["resultado_norm"] == "derrota").sum())
gp = int(filtrado[cols["gols_pro"]].sum())
gc = int(filtrado[cols["gols_contra"]].sum())
saldo_total = gp - gc
aprov = percentual(vit * 3 + emp, total * 3)
media_total = round((gp + gc) / total, 2)
media_pro = round(gp / total, 2) if total else 0
media_contra = round(gc / total, 2) if total else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
kpis = [
    ("Jogos", fmt_int(total)),
    ("Vitórias", fmt_int(vit)),
    ("Empates", fmt_int(emp)),
    ("Derrotas", fmt_int(der)),
    ("Aproveitamento", f"{str(aprov).replace('.', ',')}%"),
    ("Média total", fmt_float(media_total, 2)),
]
for col, (label, value) in zip([k1, k2, k3, k4, k5, k6], kpis):
    with col:
        st.markdown(
            f"""
            <div class="kpi">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

aba1, aba2, aba3 = st.tabs(["Resumo", "Confrontos", "Lista de jogos"])

# =========================================================
# ABA 1 - RESUMO
# =========================================================
with aba1:
    ctop1, ctop2, ctop3 = st.columns([2.2, 1, 1])

    with ctop1:
        st.markdown('<div class="section-title">Forma recente</div>', unsafe_allow_html=True)
        ultimos = filtrado.tail(10)

        html = ['<div class="form-wrap">']
        for _, row in ultimos.iterrows():
            r = row["resultado_norm"]
            cor = "#22c55e" if r == "vitoria" else "#eab308" if r == "empate" else "#ef4444"
            nome_res, _ = classe_resultado(r)
            tooltip = (
                f"{row[cols['adversario']]} | "
                f"{row[cols['competicao']]} | "
                f"{row[cols['temporada']]} | "
                f"{row[cols['local']]} | "
                f"{fmt_int(row[cols['gols_pro']])} x {fmt_int(row[cols['gols_contra']])} | "
                f"{nome_res}"
            )
            html.append(f'<span class="form-dot" title="{tooltip}" style="background:{cor};"></span>')
        html.append("</div>")

        st.markdown("".join(html), unsafe_allow_html=True)
        st.caption("Passe o mouse em cada bolinha para ver o jogo correspondente.")

    with ctop2:
        st.markdown(
            f"""
            <div class="card-box">
                <div class="kpi-label">Gols pró / jogo</div>
                <div class="kpi-value" style="font-size:1.8rem;">{fmt_float(media_pro, 2)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with ctop3:
        st.markdown(
            f"""
            <div class="card-box">
                <div class="kpi-label">Gols contra / jogo</div>
                <div class="kpi-value" style="font-size:1.8rem;">{fmt_float(media_contra, 2)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown(
            f"""
            <div class="card-box">
                <div class="kpi-label">Gols pró</div>
                <div class="kpi-value" style="font-size:1.9rem;">{fmt_int(gp)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with r2:
        st.markdown(
            f"""
            <div class="card-box">
                <div class="kpi-label">Gols contra</div>
                <div class="kpi-value" style="font-size:1.9rem;">{fmt_int(gc)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with r3:
        st.markdown(
            f"""
            <div class="card-box">
                <div class="kpi-label">Saldo total</div>
                <div class="kpi-value" style="font-size:1.9rem;">{fmt_int(saldo_total)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Destaques")

    melhor = filtrado.sort_values(["saldo", cols["gols_pro"]], ascending=[False, False]).iloc[0]
    pior = filtrado.sort_values(["saldo", cols["gols_pro"]], ascending=[True, True]).iloc[0]

    def render_card_resultado(titulo: str, jogo: pd.Series) -> None:
        c1, c2, c3 = st.columns([1, 6, 2])

        with c1:
            render_logo(jogo[cols["adversario"]], 52)

        with c2:
            st.markdown(f"**{titulo}**")
            st.markdown(f"**{jogo[cols['adversario']]}**")
            st.caption(
                f"{jogo[cols['competicao']]} • {jogo[cols['temporada']]} • {jogo[cols['local']]}"
            )
            render_result_tag(jogo["resultado_norm"])

        with c3:
            st.markdown(
                f'<div class="score-mid">{fmt_int(jogo[cols["gols_pro"]])} x {fmt_int(jogo[cols["gols_contra"]])}</div>',
                unsafe_allow_html=True,
            )

    with st.container(border=True):
        render_card_resultado("Melhor resultado", melhor)

    with st.container(border=True):
        render_card_resultado("Pior resultado", pior)

# =========================================================
# ABA 2 - CONFRONTOS
# =========================================================
with aba2:
    st.subheader("Histórico contra adversários")

    resumo = (
        filtrado.groupby(cols["adversario"])
        .agg(
            jogos=(cols["adversario"], "count"),
            vitorias=("resultado_norm", lambda s: int((s == "vitoria").sum())),
            empates=("resultado_norm", lambda s: int((s == "empate").sum())),
            derrotas=("resultado_norm", lambda s: int((s == "derrota").sum())),
            gols_pro=(cols["gols_pro"], "sum"),
            gols_contra=(cols["gols_contra"], "sum"),
            pontos=("pontos", "sum"),
        )
        .reset_index()
        .sort_values(["jogos", "pontos", "gols_pro"], ascending=[False, False, False])
        .head(qtd_confrontos)
    )

    resumo["aproveitamento"] = resumo.apply(
        lambda r: percentual(r["pontos"], r["jogos"] * 3),
        axis=1,
    )
    resumo["saldo"] = resumo["gols_pro"] - resumo["gols_contra"]

    for _, row in resumo.iterrows():
        time = row[cols["adversario"]]
        selecionado = st.session_state.time_selecionado == time

        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([1, 4, 3, 2, 2])

            with c1:
                render_logo(time, 44)

            with c2:
                st.markdown(f'<div class="club-name">{time}</div>', unsafe_allow_html=True)
                st.caption(f"{fmt_int(row['jogos'])} confronto(s)")
                st.caption(
                    f"Campanha: {resumo_campanha_str(row['vitorias'], row['empates'], row['derrotas'])}"
                )

            with c3:
                st.write(f"Gols: {fmt_int(row['gols_pro'])} pró / {fmt_int(row['gols_contra'])} contra")
                st.caption(f"Saldo: {fmt_int(row['saldo'])}")

            with c4:
                st.write(f"Aprov.: {str(row['aproveitamento']).replace('.', ',')}%")
                st.caption(f"Pontos: {fmt_int(row['pontos'])}")

            with c5:
                texto_botao = "Ocultar detalhes" if selecionado else "Ver detalhes"
                if st.button(texto_botao, key=f"detalhe_{time}", use_container_width=True):
                    if selecionado:
                        st.session_state.time_selecionado = None
                    else:
                        st.session_state.time_selecionado = time

    if st.session_state.time_selecionado:
        time = st.session_state.time_selecionado
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(f"Detalhamento contra {time}")

        df_time = filtrado[filtrado[cols["adversario"]] == time].copy()

        if df_time.empty:
            st.info("Nenhum jogo encontrado para esse adversário no recorte atual.")
        else:
            cab1, cab2 = st.columns([1, 8])
            with cab1:
                render_logo(time, 54)
            with cab2:
                total_time = len(df_time)
                v_time = int((df_time["resultado_norm"] == "vitoria").sum())
                e_time = int((df_time["resultado_norm"] == "empate").sum())
                d_time = int((df_time["resultado_norm"] == "derrota").sum())
                st.markdown(f"**{time}**")
                st.caption(
                    f"{fmt_int(total_time)} jogos • {resumo_campanha_str(v_time, e_time, d_time)} • "
                    f"Aproveitamento {str(percentual(v_time * 3 + e_time, total_time * 3)).replace('.', ',')}%"
                )

            detalhe = (
                df_time.groupby(cols["competicao"])
                .agg(
                    jogos=(cols["adversario"], "count"),
                    vitorias=("resultado_norm", lambda s: int((s == "vitoria").sum())),
                    empates=("resultado_norm", lambda s: int((s == "empate").sum())),
                    derrotas=("resultado_norm", lambda s: int((s == "derrota").sum())),
                    gols_pro=(cols["gols_pro"], "sum"),
                    gols_contra=(cols["gols_contra"], "sum"),
                    pontos=("pontos", "sum"),
                )
                .reset_index()
                .sort_values(["jogos", "pontos"], ascending=[False, False])
            )

            detalhe["aproveitamento"] = detalhe.apply(
                lambda r: percentual(r["pontos"], r["jogos"] * 3),
                axis=1,
            )

            st.dataframe(
                detalhe.rename(
                    columns={
                        cols["competicao"]: "Competição",
                        "jogos": "Jogos",
                        "vitorias": "Vitórias",
                        "empates": "Empates",
                        "derrotas": "Derrotas",
                        "gols_pro": "Gols pró",
                        "gols_contra": "Gols contra",
                        "pontos": "Pontos",
                        "aproveitamento": "Aproveitamento (%)",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("**Jogos contra esse adversário**")
            jogos_time = df_time.tail(12).iloc[::-1]

            for _, jogo in jogos_time.iterrows():
                j1, j2, j3 = st.columns([1, 6, 2])
                with j1:
                    render_logo(jogo[cols["adversario"]], 34)
                with j2:
                    st.markdown(f"**{jogo[cols['competicao']]}**")
                    st.caption(f"{jogo[cols['temporada']]} • {jogo[cols['local']]}")
                    render_result_tag(jogo["resultado_norm"])
                with j3:
                    st.markdown(
                        f'<div class="score-mid">{fmt_int(jogo[cols["gols_pro"]])} x {fmt_int(jogo[cols["gols_contra"]])}</div>',
                        unsafe_allow_html=True,
                    )
                st.divider()

# =========================================================
# ABA 3 - LISTA DE JOGOS
# =========================================================
with aba3:
    st.subheader("Histórico visual dos jogos")
    jogos = filtrado.tail(qtd_jogos).iloc[::-1]

    for _, jogo in jogos.iterrows():
        with st.container(border=True):
            a, b, c = st.columns([1, 7, 1.6])

            with a:
                render_logo(jogo[cols["adversario"]], 42)

            with b:
                st.markdown(f'<div class="club-name">{jogo[cols["adversario"]]}</div>', unsafe_allow_html=True)
                st.caption(f"{jogo[cols['competicao']]} • {jogo[cols['temporada']]} • {jogo[cols['local']]}")
                render_result_tag(jogo["resultado_norm"])

            with c:
                st.markdown(
                    f'<div class="score-big">{fmt_int(jogo[cols["gols_pro"]])} x {fmt_int(jogo[cols["gols_contra"]])}</div>',
                    unsafe_allow_html=True,
                )

# =========================================================
# DIAGNÓSTICO / EXPORTAÇÃO DE ESCUDOS FALTANDO
# =========================================================
if mostrar_diag:
    with st.sidebar.expander("Diagnóstico de escudos", expanded=True):
        unicos = tuple(sorted(filtrado[cols["adversario"]].astype(str).unique().tolist()))
        faltando_df = gerar_relatorio_escudos_faltando(unicos)

        st.write(f"Pasta local de escudos: {ASSETS_DIR}")
        st.write(f"Pasta existe? {'✅' if ASSETS_DIR.exists() else '❌'}")
        st.write(f"Times únicos no recorte: {fmt_int(len(unicos))}")
        st.write(f"Sem escudo encontrado: {fmt_int(len(faltando_df))}")
        st.divider()

        if faltando_df.empty:
            st.success("Todos os clubes do recorte atual têm escudo online ou local.")
        else:
            st.dataframe(faltando_df, use_container_width=True, hide_index=True)

            csv_bytes = faltando_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Baixar CSV dos clubes sem escudo",
                data=csv_bytes,
                file_name="clubes_sem_escudo.csv",
                mime="text/csv",
                use_container_width=True,
            )

            txt_buffer = StringIO()
            for _, row in faltando_df.iterrows():
                txt_buffer.write(f"{row['clube']} -> {row['slug_sugerido_arquivo']}.png\n")

            st.download_button(
                "Baixar TXT dos clubes sem escudo",
                data=txt_buffer.getvalue().encode("utf-8"),
                file_name="clubes_sem_escudo.txt",
                mime="text/plain",
                use_container_width=True,
            )

            st.caption("Se quiser preencher manualmente, salva o arquivo do escudo na pasta local com o nome sugerido.")
