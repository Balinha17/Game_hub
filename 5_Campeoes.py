import streamlit as st
import pandas as pd
import re
import unicodedata
import base64
from pathlib import Path

# =========================================================
# CONFIG
# =========================================================
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
LOGOS_DIR = DATA_DIR / "assets" / "clubes"

URL_CAMPEOES = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQstFkeNnP5dKUnfHjl2UScwn2UnIHUuGuHqx0pJMlo86ovTeqMB6wZ3MvrGGwGPkxkWzRbdPFUV90y/pub?gid=1607003330&single=true&output=csv"

COMPETICOES_NACIONAIS_ORDEM = ["Liga", "Copa", "Supercopa"]

GRUPOS_INTERNACIONAIS = {
    "UEFA": ["champions", "europa", "conference", "uefa", "supercopa uefa", "uefa super cup"],
    "CONMEBOL": ["libertadores", "sul-americana", "sulamericana", "recopa"],
    "AFC": ["afc", "asian"],
    "Mundial": ["mundial", "club world cup", "intercontinental"],
}


# =========================================================
# HELPERS
# =========================================================
def limpar_texto(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def valor_valido(valor):
    txt = limpar_texto(valor)
    return txt != "" and txt != "-"


def normalizar_nome(texto):
    if not texto:
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"[\s/]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


def inicio_temporada(temporada):
    txt = limpar_texto(temporada)
    match = re.search(r"(\d{4})", txt)
    if match:
        return int(match.group(1))
    return None


def normalizar_competicao(valor):
    return limpar_texto(valor).lower()


def eh_nacional(nome_competicao):
    return normalizar_competicao(nome_competicao) in ["liga", "copa", "supercopa"]


def grupo_internacional(nome_competicao):
    nome = normalizar_competicao(nome_competicao)

    if eh_nacional(nome):
        return ""

    for grupo, palavras in GRUPOS_INTERNACIONAIS.items():
        if any(p in nome for p in palavras):
            return grupo

    return "Outras internacionais"


def eh_internacional(nome_competicao):
    return not eh_nacional(nome_competicao)


def ordinal_br(n):
    if n == 1:
        return "maior"
    if n == 2:
        return "segundo maior"
    if n == 3:
        return "terceiro maior"
    return f"{n}º maior"


@st.cache_data(ttl=60, show_spinner="Carregando campeões do Google Sheets...")
def carregar_base():
    try:
        df = pd.read_csv(URL_CAMPEOES)
    except Exception as e:
        st.error(f"Erro ao carregar a aba Campeões do Google Sheets: {e}")
        st.stop()

    if df.empty:
        st.error("A aba Campeões veio vazia do Google Sheets.")
        st.stop()

    colunas_esperadas = [
        "Temporada", "Continente", "País", "Competição",
        "Campeão", "Vice", "Terceiro"
    ]

    faltantes = [col for col in colunas_esperadas if col not in df.columns]
    if faltantes:
        st.error(f"Faltam colunas na aba publicada do Google Sheets: {faltantes}")
        st.stop()

    df = df.copy()

    for col in colunas_esperadas:
        df[col] = df[col].apply(limpar_texto)

    df["ordem_temporada"] = df["Temporada"].apply(inicio_temporada)
    df = df[df["Temporada"] != ""].copy()
    df = df[df["Competição"] != ""].copy()
    df = df[df["Campeão"] != ""].copy()
    df["eh_internacional"] = df["Competição"].apply(eh_internacional)
    df["grupo_internacional"] = df["Competição"].apply(grupo_internacional)

    return df



@st.cache_data
def mapear_logos():
    logos = {}
    if not LOGOS_DIR.exists():
        return logos

    for arquivo in LOGOS_DIR.rglob("*.png"):
        logos[normalizar_nome(arquivo.stem)] = arquivo

    return logos


def buscar_logo(clube):
    if not valor_valido(clube):
        return None

    clube_norm = normalizar_nome(clube)
    logos = mapear_logos()

    if clube_norm in logos:
        return logos[clube_norm]

    for nome_arquivo, caminho in logos.items():
        if clube_norm == nome_arquivo or clube_norm in nome_arquivo or nome_arquivo in clube_norm:
            return caminho

    return None


@st.cache_resource
def logo_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def render_clube_inline(clube, destaque=False, logo_width=26):
    if not valor_valido(clube):
        st.markdown("<span style='color:#94a3b8;'>-</span>", unsafe_allow_html=True)
        return

    logo = buscar_logo(clube)
    cols = st.columns([0.8, 6], vertical_alignment="center")

    with cols[0]:
        if logo:
            st.image(str(logo), width=logo_width)
        else:
            st.markdown("⬜")

    with cols[1]:
        if destaque:
            st.markdown(f"**{clube}**")
        else:
            st.write(clube)


def obter_campeao_atual(df_base, competicao):
    base = df_base[df_base["Competição"] == competicao].copy()
    base = base.dropna(subset=["ordem_temporada"])

    if base.empty:
        return None

    return base.sort_values("ordem_temporada", ascending=False).iloc[0]


def calcular_maiores_campeoes(df_comp):
    if df_comp.empty:
        return pd.DataFrame()

    ranking = (
        df_comp.groupby("Campeão", as_index=False)
        .agg(
            titulos=("Campeão", "count"),
            ultimo_titulo=("ordem_temporada", "max"),
        )
        .rename(columns={"Campeão": "Clube"})
        .sort_values(["titulos", "ultimo_titulo", "Clube"], ascending=[False, False, True])
    )

    return ranking


def calcular_anos_titulos(df_comp, clube):
    base = df_comp[df_comp["Campeão"] == clube].copy()
    base = base.sort_values("ordem_temporada", ascending=False)
    return base["Temporada"].tolist()


def calcular_jejum_titulo(df_comp):
    if df_comp.empty:
        return pd.DataFrame()

    ultima_temporada = df_comp["ordem_temporada"].max()

    titulos = (
        df_comp.groupby("Campeão", as_index=False)
        .agg(
            titulos=("Campeão", "count"),
            ultima_conquista=("ordem_temporada", "max"),
        )
        .rename(columns={"Campeão": "Clube"})
    )

    titulos["temporadas_sem_titulo"] = ultima_temporada - titulos["ultima_conquista"]
    titulos = titulos.sort_values(
        ["temporadas_sem_titulo", "titulos", "Clube"],
        ascending=[False, False, True],
    )
    return titulos


def calcular_jejum_top3(df_comp):
    if df_comp.empty:
        return pd.DataFrame()

    ultima_temporada = df_comp["ordem_temporada"].max()
    registros = []

    for _, row in df_comp.iterrows():
        temporada = row["ordem_temporada"]
        for coluna in ["Campeão", "Vice", "Terceiro"]:
            clube = row[coluna]
            if valor_valido(clube):
                registros.append({"Clube": clube, "ordem_temporada": temporada})

    if not registros:
        return pd.DataFrame()

    aparicoes = pd.DataFrame(registros)

    resumo = (
        aparicoes.groupby("Clube", as_index=False)
        .agg(
            aparicoes_top3=("Clube", "count"),
            ultima_aparicao=("ordem_temporada", "max"),
        )
    )

    resumo["temporadas_fora_top3"] = ultima_temporada - resumo["ultima_aparicao"]
    resumo = resumo.sort_values(
        ["temporadas_fora_top3", "aparicoes_top3", "Clube"],
        ascending=[False, False, True],
    )
    return resumo


def calcular_trocas_lideranca(df_comp):
    if df_comp.empty:
        return pd.DataFrame()

    base = df_comp.sort_values("ordem_temporada", ascending=True).copy()

    contagem = {}
    lider_anterior = None
    eventos = []

    for _, row in base.iterrows():
        temporada = row["Temporada"]
        campeao = row["Campeão"]
        contagem[campeao] = contagem.get(campeao, 0) + 1

        maior = max(contagem.values())
        lideres = sorted([clube for clube, total in contagem.items() if total == maior])

        if len(lideres) == 1:
            lider_atual = lideres[0]
            if lider_atual != lider_anterior:
                eventos.append({
                    "Temporada": temporada,
                    "Novo líder": lider_atual,
                    "Títulos ao assumir": maior,
                })
                lider_anterior = lider_atual

    if not eventos:
        return pd.DataFrame()

    return pd.DataFrame(eventos)


def render_historico_sortable(df_hist):
    if df_hist.empty:
        st.warning("Nenhum dado encontrado para esse filtro.")
        return

    mostrar = df_hist[["Temporada", "Campeão", "Vice", "Terceiro"]].copy()
    st.dataframe(mostrar, hide_index=True, use_container_width=True)


def render_card_campeao_atual(titulo, row):
    with st.container(border=True):
        st.markdown(f"**{titulo}**")
        if row is None:
            st.write("-")
            return

        logo = buscar_logo(row["Campeão"])
        if logo:
            st.image(str(logo), width=60)
        st.markdown(f"### {row['Campeão']}")
        st.caption(f"Temporada {row['Temporada']}")


def render_ranking_card_horizontal(df_comp, titulo_bloco):
    st.markdown(f"### {titulo_bloco}")

    ranking = calcular_maiores_campeoes(df_comp).head(3)

    if ranking.empty:
        st.info("Sem dados suficientes.")
        return

    medalhas = ["🥇", "🥈", "🥉"]

    for i, (_, row) in enumerate(ranking.iterrows()):
        anos = calcular_anos_titulos(df_comp, row["Clube"])
        tooltip = " | ".join(anos) if anos else "Sem anos registrados"

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([0.7, 1.0, 4.5, 1.2], vertical_alignment="center")

            with c1:
                st.markdown(f"## {medalhas[i]}")

            with c2:
                logo = buscar_logo(row["Clube"])
                if logo:
                    st.image(str(logo), width=42)
                else:
                    st.markdown("⬜")

            with c3:
                st.markdown(f"**{row['Clube']}**")

            with c4:
                st.markdown(
                    f"<div title='{tooltip}' style='font-size:1.45rem; font-weight:800; text-align:left;'>{int(row['titulos'])}</div>",
                    unsafe_allow_html=True
                )


def render_tabela_df(df_mostrar):
    st.dataframe(df_mostrar, hide_index=True, use_container_width=True)


def render_bloco_jejum(df_comp):
    col_j1, col_j2 = st.columns(2, gap="large")

    with col_j1:
        st.markdown("### Maior jejum de título")
        jejum_titulo = calcular_jejum_titulo(df_comp)

        if jejum_titulo.empty:
            st.info("Sem dados suficientes.")
        else:
            mostrar = jejum_titulo.rename(columns={
                "titulos": "Títulos",
                "ultima_conquista": "Último título",
                "temporadas_sem_titulo": "Temporadas sem título"
            })
            render_tabela_df(mostrar[["Clube", "Títulos", "Último título", "Temporadas sem título"]])

    with col_j2:
        st.markdown("### Maior jejum de top 3")
        jejum_top3 = calcular_jejum_top3(df_comp)

        if jejum_top3.empty:
            st.info("Sem dados suficientes.")
        else:
            mostrar = jejum_top3.rename(columns={
                "aparicoes_top3": "Aparições no top 3",
                "ultima_aparicao": "Última aparição",
                "temporadas_fora_top3": "Temporadas fora do top 3"
            })
            render_tabela_df(mostrar[["Clube", "Aparições no top 3", "Última aparição", "Temporadas fora do top 3"]])


def render_trocas_lideranca(df_comp, titulo="Trocas de liderança"):
    st.markdown(f"### {titulo}")
    lideranca = calcular_trocas_lideranca(df_comp)

    if lideranca.empty:
        st.info("Sem trocas de liderança detectadas.")
    else:
        render_tabela_df(lideranca)


def calcular_resumo_clube(df_base, clube):
    titulos = df_base[df_base["Campeão"] == clube].copy()

    if titulos.empty:
        return pd.DataFrame()

    nacionais = titulos[titulos["Competição"].isin(COMPETICOES_NACIONAIS_ORDEM)].copy()
    internacionais = titulos[~titulos["Competição"].isin(COMPETICOES_NACIONAIS_ORDEM)].copy()

    resumo_nacionais = (
        nacionais.groupby(["Competição", "País"], as_index=False)
        .agg(
            Títulos=("Campeão", "count"),
            Anos=("Temporada", lambda x: " | ".join(x.tolist()))
        )
    ) if not nacionais.empty else pd.DataFrame(columns=["Competição", "País", "Títulos", "Anos"])

    resumo_internacionais = (
        internacionais.groupby(["Competição"], as_index=False)
        .agg(
            Títulos=("Campeão", "count"),
            Anos=("Temporada", lambda x: " | ".join(x.tolist()))
        )
    ) if not internacionais.empty else pd.DataFrame(columns=["Competição", "Títulos", "Anos"])

    if not resumo_internacionais.empty:
        resumo_internacionais["País"] = "-"

    resumo = pd.concat([resumo_nacionais, resumo_internacionais], ignore_index=True)
    if resumo.empty:
        return resumo

    resumo = resumo[["Competição", "País", "Títulos", "Anos"]]
    resumo = resumo.sort_values(["Títulos", "Competição", "País"], ascending=[False, True, True]).reset_index(drop=True)
    return resumo


def calcular_rankings_clube(df_base, clube):
    titulos = df_base[df_base["Campeão"] == clube].copy()
    if titulos.empty:
        return pd.DataFrame()

    registros = []

    for _, row in titulos.groupby(["Competição", "País"]).size().reset_index(name="Titulos_do_clube").iterrows():
        competicao = row["Competição"]
        pais = row["País"]
        titulos_clube = int(row["Titulos_do_clube"])

        if competicao in COMPETICOES_NACIONAIS_ORDEM:
            base_comp = df_base[(df_base["Competição"] == competicao) & (df_base["País"] == pais)].copy()
            nome_contexto = f"{competicao} da {pais}"
        else:
            base_comp = df_base[df_base["Competição"] == competicao].copy()
            nome_contexto = competicao

        ranking = calcular_maiores_campeoes(base_comp).copy()
        ranking = ranking.reset_index(drop=True)
        ranking["Posição"] = ranking.index + 1

        linha = ranking[ranking["Clube"] == clube]
        if linha.empty:
            continue

        posicao = int(linha.iloc[0]["Posição"])

        frase = f"{clube} é o {ordinal_br(posicao)} vencedor de {nome_contexto} com {titulos_clube} título"
        if titulos_clube != 1:
            frase += "s"

        registros.append({
            "Competição": competicao,
            "País": pais if competicao in COMPETICOES_NACIONAIS_ORDEM else "-",
            "Ranking": frase
        })

    if not registros:
        return pd.DataFrame()

    return pd.DataFrame(registros).sort_values(["Competição", "País"]).reset_index(drop=True)


def render_sala_trofeus(df_base, clube):
    titulos = df_base[df_base["Campeão"] == clube].copy()

    if titulos.empty:
        st.info("Esse clube ainda não tem títulos registrados na base.")
        return

    resumo = calcular_resumo_clube(df_base, clube)
    ranking_textual = calcular_rankings_clube(df_base, clube)

    total_titulos = int(len(titulos))
    nacional = titulos[titulos["Competição"].isin(COMPETICOES_NACIONAIS_ORDEM)]
    internacional = titulos[~titulos["Competição"].isin(COMPETICOES_NACIONAIS_ORDEM)]

    logo = buscar_logo(clube)
    cols = st.columns([1, 5], vertical_alignment="center")
    with cols[0]:
        if logo:
            st.image(str(logo), width=90)
    with cols[1]:
        st.markdown(f"## {clube}")
        st.markdown(f"### {total_titulos} títulos")

    st.markdown("### Sala de troféus")
    mostrar = resumo.rename(columns={"Anos": "Anos dos títulos"})
    render_tabela_df(mostrar)

    st.markdown("### Ranking por competição")
    if ranking_textual.empty:
        st.info("Sem ranking disponível.")
    else:
        render_tabela_df(ranking_textual)

    st.markdown("### Títulos por tipo")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Títulos nacionais", len(nacional))
    with c2:
        st.metric("Títulos internacionais", len(internacional))


# =========================================================
# LOAD
# =========================================================
df = carregar_base()
df_nacional = df[df["Competição"].isin(COMPETICOES_NACIONAIS_ORDEM)].copy()
df_internacional = df[~df["Competição"].isin(COMPETICOES_NACIONAIS_ORDEM)].copy()

# =========================================================
# ESTILO
# =========================================================
st.markdown("""
<style>
    .block-container {
        max-width: 1400px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏆 Campeões")
st.caption("Histórico de ligas, copas, supercopas e torneios internacionais.")

abas_principais = st.tabs([
    "📜 Histórico",
    "🌍 País",
    "🌐 Competições internacionais",
    "🏛️ Sala de troféus",
])

# =========================================================
# ABA 1 - HISTÓRICO
# =========================================================
with abas_principais[0]:
    modo_hist = st.radio(
        "Tipo de histórico",
        ["Nacional", "Internacional"],
        horizontal=True,
        key="hist_modo"
    )

    if modo_hist == "Nacional":
        col1, col2 = st.columns(2)

        with col1:
            paises = sorted(df_nacional["País"].dropna().unique().tolist())
            pais_selecionado = st.selectbox("País", paises, key="hist_pais")

        with col2:
            competicoes_pais = (
                df_nacional[df_nacional["País"] == pais_selecionado]["Competição"]
                .dropna()
                .unique()
                .tolist()
            )
            ordem = [c for c in COMPETICOES_NACIONAIS_ORDEM if c in competicoes_pais]
            resto = sorted([c for c in competicoes_pais if c not in ordem])
            competicao_selecionada = st.selectbox("Competição", ordem + resto, key="hist_comp")

        df_hist = df_nacional[
            (df_nacional["País"] == pais_selecionado) &
            (df_nacional["Competição"] == competicao_selecionada)
        ].copy()

        df_hist = df_hist.sort_values("ordem_temporada", ascending=False)

        st.subheader(f"{competicao_selecionada} - {pais_selecionado}")
        render_historico_sortable(df_hist)

    else:
        col1, col2 = st.columns(2)

        with col1:
            grupos = sorted(df_internacional["grupo_internacional"].dropna().unique().tolist())
            grupo_sel = st.selectbox("Grupo internacional", grupos, key="hist_int_grupo")

        with col2:
            comps_int = sorted(
                df_internacional[df_internacional["grupo_internacional"] == grupo_sel]["Competição"]
                .dropna()
                .unique()
                .tolist()
            )
            comp_int_hist = st.selectbox("Competição internacional", comps_int, key="hist_int_comp")

        df_hist_int = df_internacional[
            (df_internacional["grupo_internacional"] == grupo_sel) &
            (df_internacional["Competição"] == comp_int_hist)
        ].copy()

        df_hist_int = df_hist_int.sort_values("ordem_temporada", ascending=False)

        st.subheader(comp_int_hist)
        render_historico_sortable(df_hist_int)

# =========================================================
# ABA 2 - PAÍS
# =========================================================
with abas_principais[1]:
    paises = sorted(df_nacional["País"].dropna().unique().tolist())
    pais_pagina = st.selectbox("País", paises, key="pais_tab")

    df_pais = df_nacional[df_nacional["País"] == pais_pagina].copy()

    st.subheader(f"Panorama do país - {pais_pagina}")

    st.markdown("## Campeões atuais")
    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        render_card_campeao_atual("Liga", obter_campeao_atual(df_pais, "Liga"))
    with c2:
        render_card_campeao_atual("Copa", obter_campeao_atual(df_pais, "Copa"))
    with c3:
        render_card_campeao_atual("Supercopa", obter_campeao_atual(df_pais, "Supercopa"))

    st.divider()

    st.markdown("## Top 3 maiores vencedores")
    b1, b2, b3 = st.columns(3, gap="large")

    with b1:
        render_ranking_card_horizontal(df_pais[df_pais["Competição"] == "Liga"], "Liga")
    with b2:
        render_ranking_card_horizontal(df_pais[df_pais["Competição"] == "Copa"], "Copa")
    with b3:
        render_ranking_card_horizontal(df_pais[df_pais["Competição"] == "Supercopa"], "Supercopa")

    st.divider()

    comp_analise = st.selectbox(
        "Competição para análise detalhada",
        [c for c in COMPETICOES_NACIONAIS_ORDEM if c in df_pais["Competição"].unique().tolist()],
        key="pais_comp_analise"
    )

    df_pais_comp = df_pais[df_pais["Competição"] == comp_analise].copy()

    render_bloco_jejum(df_pais_comp)
    st.divider()
    render_trocas_lideranca(df_pais_comp, f"Quando alguém passou a ser o maior vencedor - {comp_analise}")

# =========================================================
# ABA 3 - INTERNACIONAIS
# =========================================================
with abas_principais[2]:
    st.subheader("Competições internacionais")

    col1, col2 = st.columns(2)

    with col1:
        grupos = sorted(df_internacional["grupo_internacional"].dropna().unique().tolist())
        grupo_sel = st.selectbox("Grupo internacional", grupos, key="int_grupo")

    with col2:
        competicoes_internacionais = sorted(
            df_internacional[df_internacional["grupo_internacional"] == grupo_sel]["Competição"]
            .dropna()
            .unique()
            .tolist()
        )

        if competicoes_internacionais:
            comp_int = st.selectbox("Competição internacional", competicoes_internacionais, key="int_comp")
        else:
            comp_int = None

    if comp_int:
        df_int_comp = df_internacional[
            (df_internacional["grupo_internacional"] == grupo_sel) &
            (df_internacional["Competição"] == comp_int)
        ].copy()

        df_int_comp = df_int_comp.sort_values("ordem_temporada", ascending=False)

        st.markdown("## Histórico")
        render_historico_sortable(df_int_comp)

        st.divider()
        st.markdown("## Top 3 maiores vencedores")
        render_ranking_card_horizontal(df_int_comp, comp_int)

        st.divider()
        render_bloco_jejum(df_int_comp)

        st.divider()
        render_trocas_lideranca(df_int_comp, f"Quando alguém passou a ser o maior vencedor - {comp_int}")
    else:
        st.info("Não encontrei competições para esse grupo.")

# =========================================================
# ABA 4 - SALA DE TROFÉUS
# =========================================================
with abas_principais[3]:
    clubes = sorted(df["Campeão"].dropna().unique().tolist())
    clube_pesquisa = st.selectbox("Clube", clubes, key="pesquisa_clube")
    render_sala_trofeus(df, clube_pesquisa)