import streamlit as st

st.set_page_config(page_title="DNA Pipeline GBIF", layout="wide")

pages = [
    st.Page("app_pages/home.py", title="Accueil", icon="🏠", default=True),
    st.Page("app_pages/dashboard.py", title="Tableau de bord", icon="📊"),
    st.Page("app_pages/validation.py", title="Validation", icon="✅"),
]
pg = st.navigation(pages)
pg.run()
