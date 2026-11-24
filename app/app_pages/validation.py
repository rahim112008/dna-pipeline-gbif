import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))
from dna_pipeline.ingest import load_data
from dna_pipeline.transform import map_to_dwc
from dna_pipeline.validate import validate_dwc, validate_mixs_terms
from dna_pipeline.publish import generate_dwca, EXT_COLS
from dna_pipeline.eml import DatasetMeta, LICENSES, validate_meta
from dna_pipeline.ui_publication import render_publication
from dna_pipeline.delivery import build_delivery_package

# Colonnes de l'extension « DNA derived data » sous leur nom interne (DNA_sequence -> dna_sequence)
EXT_INTERNAL = {"dna_sequence" if c == "DNA_sequence" else c for c in EXT_COLS}

st.title("✅ Rapport de validation")
uploaded = st.file_uploader("Fichier à valider", type=["csv", "xlsx"], key="val")

if uploaded:
    try:
        df = map_to_dwc(load_data(uploaded))
    except Exception as e:
        st.error(f"Lecture impossible : {e}")
        st.stop()
    report = validate_dwc(df)
    st.caption(f"{len(df)} ligne(s) lue(s).")

    # 1. Erreurs
    if report["errors"]:
        st.error(f"{len(report['errors'])} erreur(s) :")
        for e in report["errors"]:
            st.warning(f"{e['type']} : {e['message']}")
    else:
        st.success("Aucune erreur bloquante.")

    # 2. Avertissements
    for w in report["warnings"]:
        st.info(f"{w['type']} : {w['message']}")

    # 3. Validation MIxS (uniquement les colonnes de l'extension ADN)
    st.subheader("Validation MIxS")
    ext_df = df[["occurrenceID"] + [c for c in df.columns if c in EXT_INTERNAL]]
    mixs = validate_mixs_terms(ext_df)
    if "error" in mixs:
        st.warning(mixs["error"])
    elif mixs["valid"]:
        st.success(f"{len(mixs['valid_terms'])} termes valides dans l'extension ADN.")
    else:
        st.warning(f"Termes absents de la spécification : {mixs['invalid_terms']}")

    # 4. Métadonnées du jeu de données (EML)
    st.divider()
    st.subheader("📝 Métadonnées du jeu de données")
    st.caption("À rédiger en anglais : elles seront visibles sur GBIF.")
    title = st.text_input("Titre *")
    abstract = st.text_area("Résumé * (50 caractères minimum)", height=120)
    c1, c2 = st.columns(2)
    first = c1.text_input("Prénom de l'auteur")
    last = c2.text_input("Nom de l'auteur *")
    email = c1.text_input("Courriel de l'auteur *")
    org = c2.text_input("Organisation")
    orcid = st.text_input("ORCID (facultatif, ex. https://orcid.org/0000-0000-0000-0000)")
    lic = st.selectbox("Licence", list(LICENSES), index=1)
    sampling = st.text_area("Description de l'échantillonnage (recommandée)")

    meta = DatasetMeta(
        title=title, abstract=abstract, license=lic, sampling_description=sampling,
        publisher_org=org, creators=[{"first_name": first, "last_name": last, "email": email,
                                      "organization": org, "orcid": orcid}])
    meta_problems = validate_meta(meta)

    # 5. Génération de l'archive
    st.divider()
    st.subheader("📦 Génération du fichier final (DwC-A)")
    file_id = f"{uploaded.name}-{uploaded.size}"
    if st.session_state.get("zip_for") != file_id:      # nouveau fichier : on oublie l'ancienne archive
        st.session_state.pop("zip_data", None)

    if report["errors"]:
        st.info("Corrigez les erreurs ci-dessus pour pouvoir générer l'archive.")
    elif meta_problems:
        st.info("Complétez les métadonnées : " + " ; ".join(meta_problems))
    else:
        if st.button("Créer l'archive ZIP", type="primary"):
            try:
                with st.spinner("Création de l'archive en cours..."):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        archive_path = generate_dwca(df, tmpdir, meta)
                        st.session_state["zip_data"] = Path(archive_path).read_bytes()
                        st.session_state["zip_for"] = file_id
                        st.session_state["pub_meta"] = meta
            except Exception as e:
                st.error(f"Création impossible : {e}")

    # Le bouton de téléchargement reste affiché après un clic (état conservé)
    if st.session_state.get("zip_data") and st.session_state.get("zip_for") == file_id:
        pub_meta = st.session_state["pub_meta"]
        demo = bool("DEMO" in str(pub_meta.title).upper()
                    or df["occurrenceID"].astype(str).str.upper().str.startswith("DEMO").any()
                    or ("project_name" in df and df["project_name"].astype(str).str.upper().str.contains("DEMO").any()))
        st.success("Archive générée avec succès !")
        st.download_button("⬇️ Télécharger le fichier ZIP (Darwin Core Archive)",
                           data=st.session_state["zip_data"],
                           file_name="dna_dataset.zip", mime="application/zip")
        st.download_button(
            "📦 Télécharger le paquet de livraison (pour le partenaire)",
            data=build_delivery_package(st.session_state["zip_data"], pub_meta, df,
                                        [f"{w['type']} : {w['message']}" for w in report["warnings"]], demo),
            file_name="paquet_livraison_gbif.zip", mime="application/zip",
            help="Archive + résumé + somme de contrôle + mode d'emploi (anglais) pour l'organisation éditrice.")

        # 6. Publication sur GBIF + mise à jour
        render_publication(pub_meta, set(df["occurrenceID"].astype(str)), demo)
