import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))
from dna_pipeline.ingest import load_data
from dna_pipeline.transform import map_to_dwc
from dna_pipeline.validate import validate_dwc, validate_mixs_terms

st.title("✅ Rapport de validation")
uploaded = st.file_uploader("Fichier à valider", type=["csv", "xlsx"], key="val")
if uploaded:
    df = map_to_dwc(load_data(uploaded))
    report = validate_dwc(df)
    if report["errors"]:
        st.error(f"{len(report['errors'])} erreur(s) :")
        for e in report["errors"]:
            st.warning(f"{e['type']} : {e['message']}")
    else:
        st.success("Aucune erreur bloquante.")
    for w in report["warnings"]:
        st.info(f"{w['type']} : {w['message']}")
    st.subheader("Validation MIxS")
    mixs = validate_mixs_terms(df)
    if "error" in mixs:
        st.warning(mixs["error"])
    elif mixs["valid"]:
        st.success(f"{len(mixs['valid_terms'])} termes MIxS valides.")
    else:
        st.warning(f"Invalides : {mixs['invalid_terms']}")
