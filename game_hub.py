import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Game Hub",
    page_icon="🎮",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pages"

PAGINAS = [
    ("1_Colecao.py", "Coleção", "🎮"),
    ("2_Transferencias.py", "Transferências", "💸"),
    ("3_fm_dashboard.py", "FM Dashboard", "⚽"),
    ("4_Estatistica_Jogadores.py", "Estatística de Jogadores", "📊"),
    ("5_Campeoes.py", "Campeões", "🏆"),
]

st.markdown("""
<style>
    .block-container {
        max-width: 1250px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    .hero {
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #2563eb 100%);
        padding: 28px 32px;
        border-radius: 24px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 14px 34px rgba(0,0,0,0.22);
    }

    .hero h1 {
        margin: 0;
        font-size: 2.2rem;
    }

    .hero p {
        margin: 8px 0 0 0;
        color: #dbeafe;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>🎮 Game Hub</h1>
    <p>Escolha uma página no menu lateral para navegar pelo projeto.</p>
</div>
""", unsafe_allow_html=True)

if not PAGES_DIR.exists():
    st.error(f"Não encontrei a pasta de páginas: {PAGES_DIR}")
    st.stop()

paginas_streamlit = []

for arquivo, titulo, icone in PAGINAS:
    caminho = PAGES_DIR / arquivo

    if caminho.exists():
        paginas_streamlit.append(
            st.Page(str(caminho), title=titulo, icon=icone)
        )
    else:
        st.warning(f"Página não encontrada: {caminho}")

if not paginas_streamlit:
    st.error("Nenhuma página foi encontrada. Confira os nomes dos arquivos dentro da pasta pages.")
    st.stop()

pg = st.navigation(
    paginas_streamlit,
    position="sidebar",
    expanded=True,
)

pg.run()