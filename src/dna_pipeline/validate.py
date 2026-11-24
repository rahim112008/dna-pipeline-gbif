import hashlib
import re
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

from .transform import SPEC_RENAMES

SPEC_URL = "http://rs.gbif.org/extension/gbif/1.0/dna_derived_data_2024-07-11.xml"
CACHE_DIR = Path.home() / ".cache" / "dna_pipeline"

_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?)?)?"
                   r"(/\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?)?)?)?$")
_SEQ = re.compile(r"^[ACGTURYSWKMBDHVN.\-]+$", re.I)   # codes IUPAC inclus (amplicons dégénérés)


def _blank(s: pd.Series) -> pd.Series:
    return s.isna() | (s.astype(str).str.strip() == "")


def validate_dwc(df: pd.DataFrame) -> Dict[str, List]:
    errors, warnings = [], []
    if "occurrenceID" not in df.columns:
        return {"errors": [{"type": "Structure", "message": "Colonne occurrenceID absente."}], "warnings": []}
    if _blank(df["occurrenceID"]).any():
        errors.append({"type": "Identifiant", "message": "occurrenceID manquant sur certaines lignes."})
    if df["occurrenceID"].duplicated().any():
        dups = df[df["occurrenceID"].duplicated(keep=False)]["occurrenceID"].unique().tolist()
        errors.append({"type": "Duplication", "message": f"occurrenceID dupliqués : {dups[:5]}..."})

    for col, lim, label in (("decimalLatitude", 90, "Latitude hors [-90, 90]"),
                            ("decimalLongitude", 180, "Longitude hors [-180, 180]")):
        if col in df.columns:
            raw = df[col]
            num = pd.to_numeric(raw, errors="coerce")
            if (raw.notna() & num.isna()).any():
                errors.append({"type": "Coordonnées", "message": f"{col} contient des valeurs non numériques."})
            if (num.abs() > lim).any():
                errors.append({"type": "Coordonnées", "message": label})
    if "decimalLatitude" in df.columns and "decimalLongitude" in df.columns:
        if (df["decimalLatitude"].isna() != df["decimalLongitude"].isna()).any():
            warnings.append({"type": "Coordonnées", "message": "Latitude/longitude renseignées séparément."})

    if "eventDate" in df.columns:
        d = df["eventDate"].dropna().astype(str)
        bad = d[~d.str.match(_DATE)]
        if len(bad):
            errors.append({"type": "Date", "message": f"{len(bad)} eventDate non conformes ISO 8601 (ex. {bad.iloc[0]})."})

    if "dna_sequence" in df.columns:
        s = df["dna_sequence"]
        miss = _blank(s)
        if miss.any():
            errors.append({"type": "Séquence ADN", "message": f"{int(miss.sum())} séquences manquantes."})
        invalid = s[~miss & ~s.astype(str).str.strip().str.match(_SEQ)]
        if not invalid.empty:
            errors.append({"type": "Séquence ADN", "message": f"{len(invalid)} séquences invalides."})

    for field in ["target_gene", "seq_meth", "samp_name"]:
        if field in df.columns and df[field].isna().all():
            warnings.append({"type": "Métadonnées MIxS", "message": f"'{field}' entièrement vide."})
    for field in ["pcr_primer_forward", "pcr_primer_reverse"]:
        if field in df.columns and df[field].isna().all():
            warnings.append({"type": "Métadonnées MIxS", "message": f"Amorce '{field}' absente (recommandée)."})
    return {"errors": errors, "warnings": warnings}


def load_mixs_terms_from_spec(spec_url: str = SPEC_URL, use_cache: bool = True) -> Dict[str, str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"spec_{hashlib.md5(spec_url.encode()).hexdigest()[:10]}.xml"
    if use_cache and cache_file.exists():
        xml_content = cache_file.read_bytes()
    else:
        response = requests.get(spec_url, timeout=30)
        response.raise_for_status()
        xml_content = response.content
        cache_file.write_bytes(xml_content)
    root = ET.fromstring(xml_content)
    terms = {}
    # La spécification déclare un espace de noms par défaut : « .//property » ne trouverait rien.
    for prop in root.findall(".//{*}property"):
        name, qualname = prop.get("name"), prop.get("qualName")
        if name and qualname:
            terms[name] = qualname
    return terms


def validate_mixs_terms(df: pd.DataFrame, spec_url: str = SPEC_URL) -> Dict:
    try:
        valid_terms = load_mixs_terms_from_spec(spec_url)
    except Exception as e:
        return {"valid": False, "valid_terms": [], "invalid_terms": [], "error": str(e)}
    if not valid_terms:
        return {"valid": False, "valid_terms": [], "invalid_terms": [], "error": "Spécification vide ou illisible."}
    ext_cols = [c for c in df.columns if c != "occurrenceID"]
    spec = {c: SPEC_RENAMES.get(c, c) for c in ext_cols}     # dna_sequence -> DNA_sequence
    invalid = [c for c in ext_cols if spec[c] not in valid_terms]
    valid_found = [{"column": c, "qualname": valid_terms[spec[c]]} for c in ext_cols if spec[c] in valid_terms]
    return {"valid": len(invalid) == 0, "valid_terms": valid_found, "invalid_terms": invalid}


def validate_dwca_archive(archive_path) -> bool:
    from dwca.read import DwCAReader
    with DwCAReader(str(archive_path)) as dwca:
        assert dwca.core_rowtype is not None
        assert len(list(dwca.each_line())) > 0
    return True
