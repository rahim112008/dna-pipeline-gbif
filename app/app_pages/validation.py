import streamlit as st
import sys
from pathlib import Path
import tempfile

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))
from dna_pipeline.ingest import load_data
from dna_pipeline.transform import map_to_dwc
from dna_pipeline.validate import validate_dwc, validate_mixs_terms
from dna_pipeline.publish import generate_dwca

st.title("✅ Rapport de validation")
uploaded = st.file_uploader("Fichier à valider", type=["csv", "xlsx"], key="val")

if uploaded:
    df = map_to_dwc(load_data(uploaded))
    report = validate_dwc(df)

    # 1. Affichage des erreurs
    if report["errors"]:
        st.error(f"{len(report['errors'])} erreur(s) :")
        for e in report["errors"]:
            st.warning(f"{e['type']} : {e['message']}")
    else:
        st.success("Aucune erreur bloquante.")

    # 2. Affichage des avertissements
    for w in report["warnings"]:
        st.info(f"{w['type']} : {w['message']}")

    # 3. Validation MIxS
    st.subheader("Validation MIxS")
    mixs = validate_mixs_terms(df)
    if "error" in mixs:
        st.warning(mixs["error"])
    elif mixs["valid"]:
        st.success(f"{len(mixs['valid_terms'])} termes MIxS valides.")
    else:
        st.warning(f"Invalides : {mixs['invalid_terms']}")

    # 4. GÉNÉRATION ET TÉLÉCHARGEMENT DU FICHIER FINAL (OUTPUT)
    st.divider() # Ligne de séparation
    st.subheader("📦 Génération du fichier final (DwC-A)")
    
    if not report["errors"]:
        st.write("Vos données sont valides. Vous pouvez générer et télécharger l'archive Darwin Core prête pour GBIF.")
        
        if st.button("Créer l'archive ZIP", type="primary"):
            with st.spinner("Création de l'archive en cours..."):
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Génération de l'archive avec le module publish.py
                    archive_path = generate_dwca(df, tmpdir)
                    
                    # Lecture du fichier généré
                    with open(archive_path, "rb") as f:
                        zip_data = f.read()
                    
                    st.success("Archive générée avec succès !")
                    # Bouton de téléchargement
                    st.download_button(
                        label="⬇️ Télécharger le fichier ZIP (Darwin Core Archive)",
                        data=zip_data,
                        file_name="dna_dataset.zip",
                        mime="application/zip"
                    )
    else:
        st.info("Veuillez corriger les erreurs ci-dessus pour pouvoir générer l'archive.")
