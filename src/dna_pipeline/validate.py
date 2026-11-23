import pandas as pd
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

SPEC_URL = "http://rs.gbif.org/extension/gbif/1.0/dna_derived_data_2024-07-11.xml"
CACHE_DIR = Path.home() / ".cache" / "dna_pipeline"


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


def load_mixs_terms_from_spec(spec_url: str = SPEC_URL, use_cache: bool = True) -> Dict[str, str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "dna_derived_data_spec.xml"
    if use_cache and cache_file.exists():
        xml_content = cache_file.read_bytes()
    else:
        response = requests.get(spec_url, timeout=30)
        response.raise_for_status()
        xml_content = response.content
        cache_file.write_bytes(xml_content)
    root = ET.fromstring(xml_content)
    terms = {}
    for prop in root.findall(".//property"):
        name = prop.get("name")
        qualname = prop.get("qualName")
        if name and qualname:
            terms[name] = qualname
    return terms


def validate_mixs_terms(df: pd.DataFrame, spec_url: str = SPEC_URL) -> Dict:
    try:
        valid_terms = load_mixs_terms_from_spec(spec_url)
    except Exception as e:
        return {"valid": False, "valid_terms": [], "invalid_terms": [], "error": str(e)}
    ext_cols = [c for c in df.columns if c != "occurrenceID"]
    invalid = [c for c in ext_cols if c not in valid_terms]
    valid_found = [{"column": c, "qualname": valid_terms[c]} for c in ext_cols if c in valid_terms]
    return {"valid": len(invalid) == 0, "valid_terms": valid_found, "invalid_terms": invalid}


def validate_dwca_archive(archive_path) -> bool:
    from dwca.read import DwCAReader
    with DwCAReader(str(archive_path)) as dwca:
        assert dwca.core_rowtype is not None
        assert len(list(dwca.each_line())) > 0
    return True
