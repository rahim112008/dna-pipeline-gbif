"""Publication et mise à jour : test de l'URL, enregistrement, crawl, statut, comparaison de versions."""
from __future__ import annotations
import io
import re
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import requests

from .eml import DatasetMeta
from .publish import gbif_api_call, build_dataset_payload, GBIF_ENVS

WEB = {"uat": "https://www.gbif-uat.org", "prod": "https://www.gbif.org"}
_UUID = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")


def is_uuid(value: str) -> bool:
    return bool(_UUID.match((value or "").strip()))


def check_archive_url(url: str, timeout: int = 30) -> dict:
    """Vérifie que l'adresse renvoie DIRECTEMENT un fichier ZIP (et non une page web)."""
    out = {"ok": False, "message": "", "size": None, "final_url": url}
    if not str(url).startswith(("http://", "https://")):
        out["message"] = "L'adresse doit commencer par http:// ou https://"
        return out
    try:
        r = requests.get(url, stream=True, timeout=timeout, allow_redirects=True,
                         headers={"User-Agent": "dna-pipeline-gbif/1.0"})
    except requests.RequestException as e:
        out["message"] = f"Adresse inaccessible : {e}"
        return out
    try:
        out["final_url"] = r.url
        if r.status_code != 200:
            out["message"] = f"Le serveur répond HTTP {r.status_code} (l'adresse doit être publique)."
            return out
        head = next(r.iter_content(chunk_size=4), b"")
        out["size"] = int(r.headers["Content-Length"]) if r.headers.get("Content-Length", "").isdigit() else None
        if head != b"PK\x03\x04":
            out["message"] = ("L'adresse renvoie une page web ou un autre format, pas un ZIP. "
                              "Utilisez le lien de téléchargement direct du fichier.")
            return out
        out.update(ok=True, message="Adresse valide : le serveur renvoie bien un fichier ZIP.")
        return out
    finally:
        r.close()


def register(meta: DatasetMeta, archive_url: str, organization_key: str, installation_key: str,
             env: str, user: str, pwd: str) -> str:
    """Crée le dataset dans le registre GBIF et déclare l'archive. Identifiants passés explicitement
    (jamais stockés dans l'environnement du serveur : l'application peut être publique)."""
    if env not in GBIF_ENVS:
        raise ValueError("Environnement inconnu.")
    if not (user and pwd):
        raise ValueError("Identifiants GBIF requis.")
    if not (is_uuid(organization_key) and is_uuid(installation_key)):
        raise ValueError("Les clés d'organisation et d'installation doivent être des identifiants (UUID).")
    base, auth = GBIF_ENVS[env], (user, pwd)
    body = gbif_api_call("POST", f"{base}/dataset", json=build_dataset_payload(
        meta, organization_key.strip(), installation_key.strip()), auth=auth).json()
    key = body["key"] if isinstance(body, dict) else str(body).strip('"')
    gbif_api_call("POST", f"{base}/dataset/{key}/endpoint",
                  json={"type": "DWC_ARCHIVE", "url": archive_url}, auth=auth)
    return key


def crawl(dataset_key: str, env: str, user: str, pwd: str) -> None:
    if not is_uuid(dataset_key):
        raise ValueError("Clé de dataset invalide.")
    gbif_api_call("POST", f"{GBIF_ENVS[env]}/dataset/{dataset_key.strip()}/crawl", auth=(user, pwd))


def dataset_status(dataset_key: str, env: str) -> dict:
    if not is_uuid(dataset_key):
        raise ValueError("Clé de dataset invalide.")
    return gbif_api_call("GET", f"{GBIF_ENVS[env]}/dataset/{dataset_key.strip()}").json()


def dataset_url(dataset_key: str, env: str) -> str:
    return f"{WEB[env]}/dataset/{dataset_key}"


def core_ids(zip_bytes: bytes) -> set:
    """Identifiants occurrenceID d'une archive DwC-A, lus via son meta.xml (quel que soit le format du fichier)."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        core = ET.fromstring(z.read("meta.xml")).find("{*}core")
        loc = core.find("{*}files/{*}location").text
        sep = (core.get("fieldsTerminatedBy") or "\t").replace("\\t", "\t")
        idx = next((int(f.get("index")) for f in core.findall("{*}field")
                    if (f.get("term") or "").endswith("/occurrenceID")), None)
        if idx is None:
            idx = int(core.find("{*}id").get("index"))
        with z.open(loc) as f:
            col = pd.read_csv(f, sep=sep, skiprows=int(core.get("ignoreHeaderLines") or 0), header=None,
                              usecols=[idx], dtype=str, keep_default_na=False,
                              quotechar=core.get("fieldsEnclosedBy") or '"').iloc[:, 0]
    return set(col)


def diff_ids(old: set, new: set) -> dict:
    return {"added": len(new - old), "removed": len(old - new), "unchanged": len(old & new)}
