"""Métadonnées du jeu de données + EML 2.2 (profil GBIF). Remplace l'ancien eml_text d'une ligne."""
from __future__ import annotations
import datetime as dt
import re
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET
import pandas as pd

LICENSES = {
    "CC0-1.0": ("http://creativecommons.org/publicdomain/zero/1.0/legalcode", "Public Domain (CC0 1.0)"),
    "CC-BY-4.0": ("http://creativecommons.org/licenses/by/4.0/legalcode",
                  "Creative Commons Attribution (CC-BY) 4.0 License"),
}
_MAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FAKE = ("exemple.org", "example.org", "example.com", "chercheur@")


@dataclass
class DatasetMeta:
    title: str = ""
    abstract: str = ""
    license: str = "CC-BY-4.0"
    language: str = "en"
    creators: list = field(default_factory=list)   # [{first_name,last_name,email,organization,orcid}]
    publisher_org: str = ""
    keywords: list = field(default_factory=lambda: ["eDNA", "DNA-derived data"])
    geographic_description: str = ""
    sampling_description: str = ""
    quality_control: str = ""
    citation: str = ""
    alternate_identifier: str = ""
    prefix: str = "dataset"


def validate_meta(meta: DatasetMeta) -> list[str]:
    errs = []
    if not meta.title.strip():
        errs.append("titre manquant")
    if len(meta.abstract.strip()) < 50:
        errs.append("résumé trop court (50 caractères minimum)")
    if meta.license not in LICENSES:
        errs.append("licence : CC0-1.0 ou CC-BY-4.0 uniquement")
    if not meta.creators:
        errs.append("au moins un auteur requis")
    for c in meta.creators:
        m = c.get("email", "")
        if not c.get("last_name", "").strip():
            errs.append("auteur sans nom de famille")
        if not _MAIL.match(m) or any(f in m.lower() for f in _FAKE):
            errs.append(f"courriel invalide ou fictif : « {m} »")
    return errs


def _p(parent, tag, text=None, **attrs):
    e = ET.SubElement(parent, tag, {k: v for k, v in attrs.items() if v})
    if text not in (None, ""):
        e.text = str(text)
    return e


def _party(parent, tag, c):
    e = _p(parent, tag)
    if c.get("last_name") or c.get("first_name"):
        n = _p(e, "individualName")
        _p(n, "givenName", c.get("first_name"))
        _p(n, "surName", c.get("last_name"))
    _p(e, "organizationName", c.get("organization"))
    _p(e, "electronicMailAddress", c.get("email"))
    if c.get("orcid"):
        _p(e, "userId", c["orcid"], directory="https://orcid.org/")


def build_eml(meta: DatasetMeta, occ: pd.DataFrame | None = None, today=None) -> str:
    now = today or dt.datetime.now(dt.timezone.utc)
    root = ET.Element("eml:eml", {
        "xmlns:eml": "https://eml.ecoinformatics.org/eml-2.2.0", "xmlns:dc": "http://purl.org/dc/terms/",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "https://eml.ecoinformatics.org/eml-2.2.0 https://rs.gbif.org/schema/eml-gbif-profile/1.3/eml.xsd",
        "packageId": f"{meta.prefix}/{now:%Y%m%d%H%M%S}", "system": "dna-pipeline-gbif",
        "scope": "system", "xml:lang": meta.language})
    ds = _p(root, "dataset")
    _p(ds, "alternateIdentifier", meta.alternate_identifier)
    _p(ds, "title", meta.title, **{"xml:lang": meta.language})
    for c in meta.creators:
        _party(ds, "creator", c)
    _party(ds, "metadataProvider", meta.creators[0])
    _p(ds, "pubDate", f"{now:%Y-%m-%d}")
    _p(ds, "language", meta.language)
    _p(_p(ds, "abstract"), "para", meta.abstract)
    if meta.keywords:
        ks = _p(ds, "keywordSet")
        for k in meta.keywords:
            _p(ks, "keyword", k)
        _p(ks, "keywordThesaurus", "n/a")
    url, label = LICENSES[meta.license]
    para = _p(_p(ds, "intellectualRights"), "para", "This work is licensed under a ")
    ul = _p(para, "ulink", url=url)
    _p(ul, "citetitle", label)
    ul.tail = "."
    cov = _p(ds, "coverage")
    if occ is not None and {"decimalLatitude", "decimalLongitude"} <= set(occ.columns):
        la = pd.to_numeric(occ["decimalLatitude"], errors="coerce")
        lo = pd.to_numeric(occ["decimalLongitude"], errors="coerce")
        if la.notna().any() and lo.notna().any():
            g = _p(cov, "geographicCoverage")
            _p(g, "geographicDescription", meta.geographic_description or "Sampling localities")
            b = _p(g, "boundingCoordinates")
            _p(b, "westBoundingCoordinate", f"{lo.min():.6f}")
            _p(b, "eastBoundingCoordinate", f"{lo.max():.6f}")
            _p(b, "northBoundingCoordinate", f"{la.max():.6f}")
            _p(b, "southBoundingCoordinate", f"{la.min():.6f}")
    if occ is not None and "eventDate" in occ.columns and occ["eventDate"].notna().any():
        d = occ["eventDate"].dropna().astype(str).str.split("/").explode().str[:10]
        r = _p(_p(cov, "temporalCoverage"), "rangeOfDates")
        _p(_p(r, "beginDate"), "calendarDate", d.min())
        _p(_p(r, "endDate"), "calendarDate", d.max())
    if not len(cov):
        ds.remove(cov)
    _party(ds, "contact", meta.creators[0])
    if meta.sampling_description or meta.quality_control:
        m = _p(ds, "methods")
        if meta.sampling_description:
            _p(_p(_p(m, "methodStep"), "description"), "para", meta.sampling_description)
        if meta.quality_control:
            _p(_p(_p(m, "qualityControl"), "description"), "para", meta.quality_control)
    g = _p(_p(_p(root, "additionalMetadata"), "metadata"), "gbif")
    _p(g, "dateStamp", f"{now:%Y-%m-%dT%H:%M:%S}")
    _p(g, "hierarchyLevel", "dataset")
    _p(g, "citation", meta.citation)
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
