"""Paquet de livraison pour un partenaire : archive DwC-A + résumé + somme de contrôle + mode d'emploi."""
from __future__ import annotations
import datetime as dt
import hashlib
import io
import json
import zipfile
import pandas as pd

README_EN = """\
DELIVERY PACKAGE - DNA-derived data for GBIF
============================================
{demo_banner}Dataset : {title}
Licence : {license}
Generated : {generated} (UTC) with dna-pipeline-gbif

CONTENTS
--------
dna_dataset.zip   Darwin Core Archive: Occurrence core + "DNA derived data" extension + EML metadata
summary.json      Key figures (records, samples, taxa, coverage, checksum)
checksum.sha256   SHA-256 of dna_dataset.zip (verify the file was not altered in transit)
validation.txt    Warnings raised by the pre-publication checks (empty = none)

HOW GBIF RECEIVES THE DATA
--------------------------
GBIF does not accept direct uploads of datasets: it indexes an archive that is published by an
endorsed publisher and retrieved from a stable address. Three usual routes:

A. Hosted IPT (recommended when the publisher has no server)
   Ask your GBIF node / trusted data-hosting centre for an account on its IPT. Create a resource,
   import dna_dataset.zip (or add its files), then publish and register it with GBIF.
   Please confirm with your IPT administrator that archive import is enabled on your instance.
B. Registry API (what the dna-pipeline-gbif web tool automates)
   Host dna_dataset.zip at a public, stable URL, then register the dataset with the publisher
   key and installation key. Test first on the GBIF test environment (UAT).
C. Help desk
   helpdesk@gbif.org can advise on the option that suits your organisation.

PREREQUISITE: the publishing organisation must be endorsed by GBIF (gbif.org/become-a-publisher).

BEFORE PUBLISHING
-----------------
1. Check the archive with the GBIF Data Validator (gbif.org/tools/data-validator).
2. Confirm authors, contact e-mail and licence in the metadata (eml.xml inside the archive).
3. Publish on a test environment first.

UPDATING A DATASET
------------------
Record identifiers (occurrenceID) are derived from the sample and a hash of the sequence, so they
stay identical between versions. Replace the archive (same address or same IPT resource) and ask GBIF
to re-crawl / republish. The web tool compares the previous and the new archive (added / removed /
unchanged records) before you do so.
"""


def summarize(df: pd.DataFrame, meta, zip_bytes: bytes, demo: bool = False) -> dict:
    def col(name):
        return df[name] if name in df.columns else pd.Series(dtype=object)
    lat = pd.to_numeric(col("decimalLatitude"), errors="coerce")
    lon = pd.to_numeric(col("decimalLongitude"), errors="coerce")
    dates = col("eventDate").dropna().astype(str).str.split("/").explode().str[:10]
    return {
        "title": meta.title, "license": meta.license, "demo_data": bool(demo),
        "creators": [{k: v for k, v in c.items() if v} for c in meta.creators],
        "records": int(len(df)),
        "samples": int(col("samp_name").nunique()) if "samp_name" in df.columns else None,
        "taxa": int(col("scientificName").nunique()),
        "unique_sequences": int(col("dna_sequence").nunique()) if "dna_sequence" in df.columns else None,
        "markers": sorted(col("target_gene").dropna().astype(str).unique().tolist()),
        "date_range": [dates.min(), dates.max()] if len(dates) else None,
        "bounding_box": ({"west": float(lon.min()), "east": float(lon.max()),
                          "south": float(lat.min()), "north": float(lat.max())}
                         if lat.notna().any() and lon.notna().any() else None),
        "archive": {"file": "dna_dataset.zip", "bytes": len(zip_bytes),
                    "sha256": hashlib.sha256(zip_bytes).hexdigest()},
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def build_delivery_package(zip_bytes: bytes, meta, df: pd.DataFrame, warnings=(), demo: bool = False) -> bytes:
    s = summarize(df, meta, zip_bytes, demo)
    banner = ("*** DEMONSTRATION DATA - NOT FOR PUBLICATION ***\n\n" if demo else "")
    readme = README_EN.format(demo_banner=banner, title=meta.title, license=meta.license,
                              generated=s["generated_utc"])
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("dna_dataset.zip", zip_bytes)
        z.writestr("README.txt", readme)
        z.writestr("summary.json", json.dumps(s, indent=2, ensure_ascii=False))
        z.writestr("checksum.sha256", f"{s['archive']['sha256']}  dna_dataset.zip\n")
        z.writestr("validation.txt", "\n".join(warnings) + ("\n" if warnings else ""))
    return out.getvalue()
