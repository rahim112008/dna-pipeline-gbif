import os
import time
import requests
import pandas as pd
from requests.exceptions import RequestException
from dwcawriter import Archive, Table
from pathlib import Path

OCCURRENCE_CORE_SPEC = "https://rs.gbif.org/core/dwc_occurrence_2022-02-02.xml"
DNA_EXTENSION_SPEC = "http://rs.gbif.org/extension/gbif/1.0/dna_derived_data_2024-07-11.xml"


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
    output_path = Path(output_dir) / "dna_dataset.zip"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    core_cols = ["occurrenceID", "scientificName", "decimalLatitude", "decimalLongitude", "eventDate"]
    ext_cols = ["target_gene", "seq_meth", "pcr_primer_forward", "pcr_primer_reverse",
                "dna_sequence", "taxon_id", "samp_name", "project_name",
                "env_broad_scale", "env_local_scale", "env_medium"]
    core_df = df[[c for c in core_cols if c in df.columns]].copy()
    ext_df = df[["occurrenceID"] + [c for c in ext_cols if c in df.columns]].copy()
    archive = Archive()
    archive.eml_text = "Jeu de données ADN dérivées publié via le pipeline GBIF SPLICE."
    archive.core = Table(spec=OCCURRENCE_CORE_SPEC, data=core_df, id_index=0, only_mapped_columns=True)
    if not ext_df.empty and len(ext_df.columns) > 1:
        archive.extensions.append(Table(spec=DNA_EXTENSION_SPEC, data=ext_df, id_index=0, only_mapped_columns=True))
    archive.export(str(output_path))
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
