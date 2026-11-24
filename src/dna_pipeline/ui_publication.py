"""Interface Streamlit : publication sur GBIF et mise à jour (appelée depuis la page de validation)."""
import streamlit as st

from . import gbif_tools as g
from .publish import GBIF_ENVS


def render_publication(meta, occurrence_ids: set, is_demo: bool = False):
    st.divider()
    st.subheader("🚀 Publication sur GBIF")
    with st.expander("Prérequis avant de publier"):
        st.markdown(
            "1. **Organisation endossée par GBIF** (https://www.gbif.org/become-a-publisher). "
            "Vérifiez d'abord que votre institution n'y figure pas déjà.\n"
            "2. **Clés** de l'organisation et de l'**installation** (fournies par GBIF après endossement).\n"
            "3. **Archive hébergée à une adresse publique directe** (ex. fichier joint à une *release* GitHub).\n\n"
            "Commencez toujours par l'environnement **UAT** (test, séparé de la production).")

    url = st.text_input("Adresse publique (URL directe) du fichier ZIP", key="pub_url")
    if st.button("Tester l'adresse"):
        res = g.check_archive_url(url)
        (st.success if res["ok"] else st.error)(res["message"])

    env = st.radio("Environnement GBIF", list(GBIF_ENVS), horizontal=True, key="pub_env",
                   format_func=lambda e: "UAT (test)" if e == "uat" else "PRODUCTION")
    c1, c2 = st.columns(2)
    org = c1.text_input("Clé de l'organisation (UUID)", key="pub_org")
    inst = c1.text_input("Clé de l'installation (UUID)", key="pub_inst")
    user = c2.text_input("Utilisateur GBIF", key="pub_user")
    pwd = c2.text_input("Mot de passe GBIF", type="password", key="pub_pwd")
    st.caption("Vos identifiants ne sont ni enregistrés ni partagés : ils servent uniquement à cet envoi.")
    prod_ok = st.checkbox("Je confirme vouloir publier en PRODUCTION", key="pub_prod") if env == "prod" else True

    if st.button("Enregistrer le dataset sur GBIF", type="primary"):
        if is_demo:
            st.error("Ces données sont marquées « DEMO » : publication bloquée.")
        elif not prod_ok:
            st.error("Cochez la confirmation pour publier en production.")
        else:
            res = g.check_archive_url(url)
            if not res["ok"]:
                st.error(res["message"])
            else:
                try:
                    key = g.register(meta, url, org, inst, env, user, pwd)
                    st.session_state["pub_key"] = key
                    st.success(f"Dataset enregistré : {key}")
                    st.markdown(f"[Ouvrir la page du dataset]({g.dataset_url(key, env)})")
                except Exception as e:
                    st.error(f"Enregistrement impossible : {e}")

    st.subheader("🔄 Mise à jour")
    st.caption("Comparez avec la version déjà publiée, remplacez le ZIP à la MÊME adresse, puis demandez un nouveau crawl.")
    key = st.text_input("Clé du dataset (UUID)", key="pub_key")
    old = st.file_uploader("Archive précédente (.zip)", type="zip", key="pub_old")
    if old:
        try:
            d = g.diff_ids(g.core_ids(old.getvalue()), set(occurrence_ids))
            a, b, c = st.columns(3)
            a.metric("Ajoutées", d["added"]); b.metric("Retirées", d["removed"]); c.metric("Inchangées", d["unchanged"])
        except Exception as e:
            st.error(f"Comparaison impossible : {e}")
    d1, d2 = st.columns(2)
    if d1.button("Demander un nouveau crawl"):
        try:
            g.crawl(key, env, user, pwd)
            st.success("Crawl demandé : l'indexation peut prendre quelques minutes.")
        except Exception as e:
            st.error(f"Crawl impossible : {e}")
    if d2.button("Voir le statut"):
        try:
            s = g.dataset_status(key, env)
            st.json({k: s.get(k) for k in ("key", "title", "modified", "license", "publishingOrganizationKey")})
        except Exception as e:
            st.error(f"Statut indisponible : {e}")
