import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Minha Coleção de Jogos",
    page_icon="🎮",
    layout="wide"
)

# =========================================================
# CAMINHOS PORTÁTEIS
# =========================================================
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

CAMINHO_PLANILHA = DATA_DIR / "Coleção de games - 2.0.xlsx"

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    .hero {
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 60%, #2563eb 100%);
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

    .section-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px 18px 8px 18px;
        margin-bottom: 18px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def listar_abas(caminho_arquivo):
    return pd.ExcelFile(caminho_arquivo).sheet_names


@st.cache_data
def carregar_excel(caminho_arquivo, aba):
    df = pd.read_excel(caminho_arquivo, sheet_name=aba)
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df


def norm(serie):
    return serie.astype(str).str.strip().str.lower()


def percentual(parte, total):
    if total == 0:
        return 0.0
    return round((parte / total) * 100, 1)


def simplificar_plataforma(nome):
    mapa = {
        "nintendo - 3ds": "3DS",
        "nintendo - ds": "DS",
        "nintendo - gameboy": "GB",
        "nintendo - gameboy advance": "GBA",
        "nintendo - gamecube": "GC",
        "nintendo - nes": "NES",
        "nintendo - super nintendo": "SNES",
        "nintendo - switch": "Switch",
        "nintendo - wii": "Wii",
        "nintendo - wiiu": "WiiU",
        "pc": "PC",
        "sega dreamcast": "Dreamcast",
        "sony - playstation": "PS1",
        "sony - playstation 2": "PS2",
        "sony - playstation 3": "PS3",
        "sony - playstation 4": "PS4",
        "sony - playstation 5": "PS5",
        "sony - playstation portable": "PSP",
        "sony - playstation vita": "PS Vita",
        "xbox 360": "Xbox 360",
    }
    chave = str(nome).strip().lower()
    return mapa.get(chave, str(nome).strip())


st.markdown("""
<div class="hero">
    <h1>🎮 Minha Coleção de Jogos</h1>
    <p>Resumo visual da coleção, wishlist e jogos zerados por plataforma.</p>
</div>
""", unsafe_allow_html=True)

if not CAMINHO_PLANILHA.exists():
    st.error(f"Planilha não encontrada em: {CAMINHO_PLANILHA}")
    st.info("Coloque o arquivo dentro da pasta data do projeto.")
    st.stop()

abas = listar_abas(CAMINHO_PLANILHA)
aba_escolhida = st.selectbox("Escolha a aba da planilha", abas)

df = carregar_excel(CAMINHO_PLANILHA, aba_escolhida)

if "jogo" not in df.columns or "plataforma" not in df.columns:
    st.error("Sua planilha precisa ter as colunas 'jogo' e 'plataforma'.")
    st.stop()

if "tenho" not in df.columns:
    df["tenho"] = "Não"

if "zerado" not in df.columns:
    df["zerado"] = "Não"

df["plataforma_curta"] = df["plataforma"].apply(simplificar_plataforma)

df["tenho_norm"] = norm(df["tenho"])
df["zerado_norm"] = norm(df["zerado"])

df["tenho_bool"] = df["tenho_norm"].eq("sim")
df["zerado_bool"] = df["zerado_norm"].eq("sim")

df_filtrado = df.copy()

st.sidebar.header("Filtros")

busca_nome = st.sidebar.text_input("Pesquisar jogo")
if busca_nome:
    df_filtrado = df_filtrado[
        df_filtrado["jogo"].astype(str).str.contains(busca_nome, case=False, na=False)
    ]

plataformas = sorted(df["plataforma_curta"].dropna().astype(str).unique())
plataforma_filtro = st.sidebar.multiselect("Console", plataformas)
if plataforma_filtro:
    df_filtrado = df_filtrado[df_filtrado["plataforma_curta"].isin(plataforma_filtro)]

filtro_tenho = st.sidebar.selectbox("Tenho?", ["Todos", "Sim", "Não"])
if filtro_tenho != "Todos":
    alvo = filtro_tenho.lower()
    if alvo == "não":
        df_filtrado = df_filtrado[df_filtrado["tenho_norm"].isin(["não", "nao"])]
    else:
        df_filtrado = df_filtrado[df_filtrado["tenho_norm"] == alvo]

filtro_zerado = st.sidebar.selectbox("Zerado?", ["Todos", "Sim", "Não"])
if filtro_zerado != "Todos":
    alvo = filtro_zerado.lower()
    if alvo == "não":
        df_filtrado = df_filtrado[df_filtrado["zerado_norm"].isin(["não", "nao"])]
    else:
        df_filtrado = df_filtrado[df_filtrado["zerado_norm"] == alvo]

ordenacao = st.sidebar.selectbox(
    "Ordenar resumo por",
    ["A-Z", "Maior total", "Maior coleção", "Maior zeramento"]
)

total_jogos = len(df_filtrado)
jogos_tenho = int(df_filtrado["tenho_bool"].sum())
wishlist = int(df_filtrado["tenho_norm"].isin(["não", "nao"]).sum())
zerados = int(df_filtrado["zerado_bool"].sum())

taxa_colecao = percentual(jogos_tenho, total_jogos)
taxa_zerados_sobre_tenho = percentual(zerados, jogos_tenho) if jogos_tenho > 0 else 0.0
taxa_zerados_sobre_total = percentual(zerados, total_jogos)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de jogos", total_jogos)
c2.metric("Jogos que tenho", jogos_tenho)
c3.metric("Wishlist", wishlist)
c4.metric("Jogos zerados", zerados)

c5, c6, c7 = st.columns(3)
c5.metric("% da coleção já comprada", f"{taxa_colecao}%")
c6.metric("% zerado do que você tem", f"{taxa_zerados_sobre_tenho}%")
c7.metric("% zerado do total listado", f"{taxa_zerados_sobre_total}%")

resumo = (
    df_filtrado.groupby("plataforma_curta")
    .agg(
        total=("jogo", "count"),
        tenho=("tenho_bool", "sum"),
        zerado=("zerado_bool", "sum"),
    )
    .reset_index()
)

resumo["wishlist"] = resumo["total"] - resumo["tenho"]
resumo["nao_zerado"] = resumo["tenho"] - resumo["zerado"]
resumo["perc_colecao"] = resumo.apply(lambda row: percentual(row["tenho"], row["total"]), axis=1)
resumo["perc_zerado"] = resumo.apply(
    lambda row: percentual(row["zerado"], row["tenho"]) if row["tenho"] > 0 else 0.0,
    axis=1
)

if ordenacao == "A-Z":
    resumo = resumo.sort_values("plataforma_curta")
elif ordenacao == "Maior total":
    resumo = resumo.sort_values("total", ascending=False)
elif ordenacao == "Maior coleção":
    resumo = resumo.sort_values("perc_colecao", ascending=False)
else:
    resumo = resumo.sort_values("perc_zerado", ascending=False)

aba_resumo, aba_graficos, aba_tabela = st.tabs(["📌 Resumo", "📊 Gráficos", "📋 Tabelas"])

with aba_resumo:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Resumo geral")

    if total_jogos == 0:
        st.warning("Nenhum dado encontrado com os filtros atuais.")
    else:
        plataforma_mais_jogos = resumo.sort_values("total", ascending=False).iloc[0]
        plataforma_mais_tenho = resumo.sort_values("tenho", ascending=False).iloc[0]
        plataformas_com_100_colecao = int((resumo["perc_colecao"] >= 100).sum())
        plataformas_com_100_zerado = int((resumo["perc_zerado"] >= 100).sum())
        plataformas_sem_nada = int((resumo["tenho"] == 0).sum())

        st.write(
            f"""
            Você tem **{jogos_tenho}** jogos de um total de **{total_jogos}** cadastrados,
            o que representa **{taxa_colecao}%** da coleção atual.
            Desses jogos que você possui, **{zerados}** já foram zerados,
            equivalente a **{taxa_zerados_sobre_tenho}%** do que está na sua estante.
            """
        )

        st.write(
            f"""
            A plataforma com mais jogos cadastrados é **{plataforma_mais_jogos['plataforma_curta']}**
            com **{int(plataforma_mais_jogos['total'])}** jogos.
            A plataforma em que você mais possui jogos é **{plataforma_mais_tenho['plataforma_curta']}**
            com **{int(plataforma_mais_tenho['tenho'])}** títulos já na coleção.
            """
        )

        st.write(
            f"""
            Hoje você tem **{plataformas_com_100_colecao}** plataforma(s) com coleção completa,
            **{plataformas_com_100_zerado}** plataforma(s) com tudo zerado
            e **{plataformas_sem_nada}** plataforma(s) onde ainda não possui nenhum jogo listado.
            """
        )

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Melhores e piores plataformas")

    if not resumo.empty:
        top_colecao = resumo[resumo["total"] > 0].sort_values("perc_colecao", ascending=False).head(5)
        top_zerado = resumo[resumo["tenho"] > 0].sort_values("perc_zerado", ascending=False).head(5)
        maior_wishlist = resumo.sort_values("wishlist", ascending=False).head(5)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Maior progresso de coleção**")
            st.dataframe(
                top_colecao[["plataforma_curta", "tenho", "total", "perc_colecao"]].rename(columns={
                    "plataforma_curta": "Console",
                    "tenho": "Tenho",
                    "total": "Total",
                    "perc_colecao": "% Coleção"
                }),
                use_container_width=True,
                hide_index=True
            )

        with col2:
            st.markdown("**Maior progresso de zeramento**")
            st.dataframe(
                top_zerado[["plataforma_curta", "zerado", "tenho", "perc_zerado"]].rename(columns={
                    "plataforma_curta": "Console",
                    "zerado": "Zerados",
                    "tenho": "Tenho",
                    "perc_zerado": "% Zerado"
                }),
                use_container_width=True,
                hide_index=True
            )

        with col3:
            st.markdown("**Maior wishlist**")
            st.dataframe(
                maior_wishlist[["plataforma_curta", "wishlist", "total"]].rename(columns={
                    "plataforma_curta": "Console",
                    "wishlist": "Wishlist",
                    "total": "Total"
                }),
                use_container_width=True,
                hide_index=True
            )

    st.markdown('</div>', unsafe_allow_html=True)

with aba_graficos:
    if resumo.empty:
        st.warning("Nenhum dado encontrado com os filtros atuais.")
    else:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Jogos por plataforma")
        graf_total = resumo.set_index("plataforma_curta")[["total"]].sort_values("total", ascending=False)
        st.bar_chart(graf_total)
        st.caption("Mostra o tamanho total da sua lista em cada console.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Tenho x Wishlist por plataforma")
        graf_colecao = resumo.set_index("plataforma_curta")[["tenho", "wishlist"]].sort_values("tenho", ascending=False)
        st.bar_chart(graf_colecao)
        st.caption("Compara o que já está na coleção com o que ainda falta comprar.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Zerados x Não zerados")
        graf_zeramento = resumo.set_index("plataforma_curta")[["zerado", "nao_zerado"]].sort_values("zerado", ascending=False)
        st.bar_chart(graf_zeramento)
        st.caption("Mostra quanto da sua coleção de cada console já foi concluída.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Percentual de coleção por plataforma")
        graf_perc_colecao = resumo.set_index("plataforma_curta")[["perc_colecao"]].sort_values("perc_colecao", ascending=False)
        st.bar_chart(graf_perc_colecao)
        st.caption("Percentual de jogos possuídos sobre o total listado em cada console.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Percentual de zeramento por plataforma")
        graf_perc_zerado = resumo[resumo["tenho"] > 0].set_index("plataforma_curta")[["perc_zerado"]].sort_values("perc_zerado", ascending=False)
        st.bar_chart(graf_perc_zerado)
        st.caption("Percentual de jogos zerados dentro do que você já possui.")
        st.markdown('</div>', unsafe_allow_html=True)

with aba_tabela:
    st.subheader("Resumo por console")

    tabela_resumo = resumo.rename(columns={
        "plataforma_curta": "Console",
        "total": "Total",
        "tenho": "Tenho",
        "wishlist": "Wishlist",
        "zerado": "Zerados",
        "nao_zerado": "Não zerados",
        "perc_colecao": "% Coleção",
        "perc_zerado": "% Zerado"
    })

    st.dataframe(tabela_resumo, use_container_width=True, height=420, hide_index=True)

    st.subheader("Tabela completa")
    st.dataframe(df_filtrado, use_container_width=True, height=420, hide_index=True)
