
---

## 📋 Fichier 16/28 — `app/app_pages/dashboard.py`

**Nom à taper :** `app/app_pages/dashboard.py`

**Contenu :**
```python
import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))
from dna_pipeline.ingest import load_data
from dna_pipeline.transform import map_to_dwc

st.title("📊 Tableau de bord des données ADN")

uploaded = st.file_uploader("Chargez un CSV ou Excel", type=["csv", "xlsx"])
if uploaded:
    df = map_to_dwc(load_data(uploaded))
    c1, c2, c3 = st.columns(3)
    c1.metric("Enregistrements", len(df))
    c2.metric("Colonnes mappées", len(df.columns))
    c3.metric("Champs ADN", df[["target_gene", "dna_sequence"]].notna().sum().sum())
    st.dataframe(df.head(20))
    if "target_gene" in df.columns:
        counts = df["target_gene"].value_counts().reset_index()
        counts.columns = ["Gène", "Nombre"]
        st.bar_chart(counts.set_index("Gène"))
else:
    st.info("Chargez un fichier pour démarrer.")
