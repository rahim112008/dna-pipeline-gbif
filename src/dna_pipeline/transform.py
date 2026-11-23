import pandas as pd


COLUMN_MAPPING = {
    "occurrence_id": "occurrenceID",
    "scientific_name": "scientificName",
    "lat": "decimalLatitude",
    "latitude": "decimalLatitude",
    "lon": "decimalLongitude",
    "longitude": "decimalLongitude",
    "date": "eventDate",
    "event_date": "eventDate",
    "target_gene": "target_gene",
    "gene": "target_gene",
    "marker": "target_gene",
    "seq_meth": "seq_meth",
    "sequencing_method": "seq_meth",
    "primer_f": "pcr_primer_forward",
    "primer_r": "pcr_primer_reverse",
    "sequence": "dna_sequence",
    "dna_sequence": "dna_sequence",
    "taxon_id": "taxon_id",
    "ncbi_taxon_id": "taxon_id",
    "sample_name": "samp_name",
    "project": "project_name",
    "env_broad_scale": "env_broad_scale",
    "env_local_scale": "env_local_scale",
    "env_medium": "env_medium",
}


def map_to_dwc(df: pd.DataFrame) -> pd.DataFrame:
    df_mapped = df.rename(columns={k: v for k, v in COLUMN_MAPPING.items() if k in df.columns})
    if "occurrenceID" not in df_mapped.columns:
        raise ValueError("Colonne obligatoire manquante : occurrenceID")
    for term in set(COLUMN_MAPPING.values()):
        if term not in df_mapped.columns:
            df_mapped[term] = None
    ordered = ["occurrenceID"] + [c for c in df_mapped.columns if c != "occurrenceID"]
    return df_mapped[ordered]
