import hashlib
import re
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

# Alias supplémentaires : renommés s'ils sont présents, mais NON ajoutés en colonnes vides
# (le comportement historique de map_to_dwc reste donc inchangé).
EXTRA_MAPPING = {
    "reads": "organismQuantity", "read_count": "organismQuantity", "organism_quantity": "organismQuantity",
    "basis_of_record": "basisOfRecord", "country_code": "countryCode", "locality": "locality",
    "primer_forward": "pcr_primer_forward", "primer_reverse": "pcr_primer_reverse",
}

# Nom interne -> nom exact dans la spécification GBIF « DNA derived data » (sensible à la casse)
SPEC_RENAMES = {"dna_sequence": "DNA_sequence"}


def make_occurrence_id(prefix: str, sample, sequence) -> str:
    """Identifiant stable : préfixe + échantillon + hash de la séquence (identique d'une livraison à l'autre)."""
    h = hashlib.md5(str(sequence).strip().upper().encode()).hexdigest()[:16]
    return re.sub(r"[^A-Za-z0-9._:-]", "_", f"{prefix}:{sample}:{h}")


def map_to_dwc(df: pd.DataFrame, id_prefix: str | None = None) -> pd.DataFrame:
    mapping = {**COLUMN_MAPPING, **EXTRA_MAPPING}
    df_mapped = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
    if "occurrenceID" not in df_mapped.columns:
        if id_prefix and "dna_sequence" in df_mapped.columns:
            samples = df_mapped["samp_name"] if "samp_name" in df_mapped.columns else range(len(df_mapped))
            df_mapped.insert(0, "occurrenceID", [make_occurrence_id(id_prefix, s, q)
                                                 for s, q in zip(samples, df_mapped["dna_sequence"])])
        else:
            raise ValueError("Colonne obligatoire manquante : occurrenceID")
    for term in set(COLUMN_MAPPING.values()):
        if term not in df_mapped.columns:
            df_mapped[term] = None
    if "dna_sequence" in df_mapped.columns:   # espaces parasites / minuscules
        df_mapped["dna_sequence"] = df_mapped["dna_sequence"].map(
            lambda s: re.sub(r"\s+", "", s).upper() if isinstance(s, str) else s)
    ordered = ["occurrenceID"] + [c for c in df_mapped.columns if c != "occurrenceID"]
    return df_mapped[ordered]
