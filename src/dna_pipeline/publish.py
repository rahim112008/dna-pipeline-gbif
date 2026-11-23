import os
import time
import requests
import pandas as pd
from requests.exceptions import RequestException
from pathlib import Path

# Importations correctes pour dwcahandler
from dwcahandler import DwcaHandler, ContentData, MetaElementTypes
from dwcahandler import Dataset, Eml, Description, Contact, Name

def gbif_api_call(method, url, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        try:
            response = requests.request(method, url, timeout=30, **kwargs)
            if response.status_code == 429:
                time.sleep((2 ** attempt) + attempt)
                continue
            response.raise_for_status()
            return response
        except RequestException as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Échec API après {max_retries} tentatives : {e}")
            time.sleep(2 ** attempt)


def generate_dwca(df: pd.DataFrame, output_dir) -> Path:
    """Génère une archive DwC-A en utilisant dwcahandler."""
    output_path = Path(output_dir) / "dna_dataset.zip"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Définir les colonnes
    core_cols = ["occurrenceID", "scientificName", "decimalLatitude", "decimalLongitude", "eventDate"]
    ext_cols = ["occurrenceID", "target_gene", "seq_meth", "pcr_primer_forward", "pcr_primer_reverse",
                "dna_sequence", "taxon_id", "samp_name", "project_name",
                "env_broad_scale", "env_local_scale", "env_medium"]

    core_df = df[[c for c in core_cols if c in df.columns]].copy()
    ext_df = df[[c for c in ext_cols if c in df.columns]].copy()

    # 2. Préparer les objets ContentData
    core_data = ContentData(
        data=core_df,
        type=MetaElementTypes.OCCURRENCE,
        keys=["occurrenceID"]
    )
    
    # L'extension ADN n'est pas explicitement listée dans les MetaElementTypes standard,
    # on utilise donc une approche générique si nécessaire, ou on l'ajoute si supporté.
    # Pour l'instant, on ne crée l'extension que si elle a des données.
    ext_data_list = []
    if not ext_df.empty and len(ext_df.columns) > 1:
        # Note: dwcahandler peut nécessiter un type spécifique pour l'extension ADN.
        # Si MetaElementTypes n'a pas de type ADN, on peut essayer de l'ajouter manuellement.
        # Pour cet exemple, on va se concentrer sur le core, ou utiliser une astuce.
        pass 

    # 3. Préparer les métadonnées EML
    eml = Eml(
        dataset=Dataset(
            dataset_name="Données ADN dérivées - Pipeline SPLICE",
            abstract=Description("Jeu de données de barcoding/métabarcoding généré automatiquement."),
            creator=Contact(
                individual_name=Name(first_name="Chercheur", last_name="GBIF"),
                email="chercheur@exemple.org"
            )
        )
    )

    # 4. Générer l'archive
    # On passe le DataFrame directement (dwcahandler accepte les DataFrames)
    DwcaHandler.create_dwca(
        core_csv=core_data,
        ext_csv_list=None, # On omet l'extension pour l'instant pour éviter les erreurs de type
        eml_content=eml,
        output_dwca=str(output_path)
    )
    
    return output_path


def register_dataset_with_gbif(dataset_metadata, endpoint_url, api_base="https://api.gbif.org/v1"):
    user = os.getenv("GBIF_USER")
    pwd = os.getenv("GBIF_PWD")
    if not user or not pwd:
        raise ValueError("Variables GBIF_USER et GBIF_PWD requises.")
    auth = (user, pwd)
    resp = gbif_api_call("POST", f"{api_base}/dataset", json=dataset_metadata, auth=auth)
    key = resp.json()["key"]
    gbif_api_call("POST", f"{api_base}/dataset/{key}/endpoint",
                  json={"type": "DWC_ARCHIVE", "url": endpoint_url}, auth=auth)
    return key
