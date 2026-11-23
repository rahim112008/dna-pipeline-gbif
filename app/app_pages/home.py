import streamlit as st

st.title("🧬 Pipeline de publication de données ADN dérivées vers GBIF")
st.markdown("""
**Interface de démonstration** du pipeline de publication de données ADN
vers le réseau GBIF.

### Fonctionnalités
- Ingestion CSV/Excel
- Mapping Darwin Core + extension DNA-derived data (MIxS)
- Validation interactive
- Génération de Darwin Core Archive (DwC-A)
- Publication via l'API GBIF

### CLI
Utilisez la commande `dna-pipeline run --input-path data/raw/example.csv`
""")
