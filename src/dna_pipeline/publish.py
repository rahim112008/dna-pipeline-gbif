import os
import time
import requests
import pandas as pd
from requests.exceptions import RequestException
from pathlib import Path

# Importations correctes selon la documentation officielle de dwcahandler
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
    """Génère une archive DwC-A en utilisant la bibliothèque dwcahandler."""
    output_path = Path(output_dir) / "dna_dataset.zip"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Préparation des données (DataFrames)
    core_cols = ["occurrenceID", "scientificName", "decimalLatitude", "decimalLongitude", "eventDate"]
    core_df = df[[c for c in core_cols if c in df.columns]].copy()

    # 2. Création de l'objet ContentData pour le core (Occurrence)
    core_csv = ContentData(
        data=core_df,
        type=MetaElementTypes.OCCURRENCE,
        keys=["occurrenceID"]
    )

    # 3. Création de l'objet Eml (métadonnées obligatoires)
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

    # 4. Génération de l'archive avec la méthode officielle
    DwcaHandler.create_dwca(
        core_csv=core_csv,
        ext_csv_list=None,  # On omet l'extension ADN pour l'instant (le core fonctionnera)
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
