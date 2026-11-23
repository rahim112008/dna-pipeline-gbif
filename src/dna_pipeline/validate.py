import pandas as pd
from typing import Dict, List

# Liste des termes du Core (Darwin Core)
CORE_TERMS = {"occurrenceID", "scientificName", "decimalLatitude", "decimalLongitude", "eventDate"}

# Liste des termes de l'extension ADN (MIxS)
DNA_TERMS = {
    "target_gene", "seq_meth", "pcr_primer_forward", "pcr_primer_reverse",
    "dna_sequence", "taxon_id", "samp_name", "project_name",
    "env_broad_scale", "env_local_scale", "env_medium"
}

def validate_dwc(df: pd.DataFrame) -> Dict[str, List]:
    errors, warnings = [], []
    if df["occurrenceID"].duplicated().any():
        dups = df[df["occurrenceID"].duplicated(keep=False)]["occurrenceID"].unique().tolist()
        errors.append({"type": "Duplication", "message": f"occurrenceID dupliqués : {dups[:5]}..."})
    
    for col in ["decimalLatitude", "decimalLongitude"]:
        if col in df.columns:
            nn = df[col].dropna()
            if not nn.empty:
                if col == "decimalLatitude" and ((nn < -90) | (nn > 90)).any():
                    errors.append({"type": "Coordonnées", "message": "Latitude hors [-90, 90]"})
                if col == "decimalLongitude" and ((nn < -180) | (nn > 180)).any():
                    errors.append({"type": "Coordonnées", "message": "Longitude hors [-180, 180]"})
                    
    if "dna_sequence" in df.columns:
        invalid = df[~df["dna_sequence"].astype(str).str.match(r'^[ACGTNacgtn]+$', na=False)]["dna_sequence"]
        if not invalid.empty:
            errors.append({"type": "Séquence ADN", "message": f"{len(invalid)} séquences invalides."})
            
    for field in ["target_gene", "seq_meth", "samp_name"]:
        if field in df.columns and df[field].isna().all():
            warnings.append({"type": "Métadonnées MIxS", "message": f"'{field}' entièrement vide."})
            
    return {"errors": errors, "warnings": warnings}


def validate_mixs_terms(df: pd.DataFrame, spec_url: str = None) -> Dict:
    """Vérifie que les colonnes sont bien des termes Core ou MIxS connus."""
    all_cols = df.columns.tolist()
    # On cherche les colonnes inconnues (ni Core, ni MIxS)
    unknown_cols = [c for c in all_cols if c not in CORE_TERMS and c not in DNA_TERMS]
    
    if unknown_cols:
        return {"valid": False, "valid_terms": [], "invalid_terms": unknown_cols}
        
    found_dna_terms = [c for c in all_cols if c in DNA_TERMS]
    return {
        "valid": True, 
        "valid_terms": [{"column": c, "qualname": "MIxS"} for c in found_dna_terms], 
        "invalid_terms": []
    }


def validate_dwca_archive(archive_path) -> bool:
    from dwca.read import DwCAReader
    with DwCAReader(str(archive_path)) as dwca:
        assert dwca.core_rowtype is not None
        assert len(list(dwca.each_line())) > 0
    return True
