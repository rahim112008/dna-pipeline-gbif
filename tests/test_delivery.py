import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from dna_pipeline.delivery import build_delivery_package
from dna_pipeline.eml import DatasetMeta
from dna_pipeline.transform import map_to_dwc

META = DatasetMeta(title="Test", abstract="x" * 60, creators=[{"last_name": "B", "email": "a@b.dz"}])
DF = map_to_dwc(pd.read_csv(Path(__file__).parents[1] / "data" / "raw" / "example.csv"))


def _open(demo=False, warnings=()):
    pkg = build_delivery_package(b"PK-fake-archive", META, DF, warnings, demo)
    return zipfile.ZipFile(io.BytesIO(pkg))


def test_package_contents_and_checksum():
    z = _open(warnings=["Métadonnées MIxS : x"])
    assert set(z.namelist()) == {"dna_dataset.zip", "README.txt", "summary.json", "checksum.sha256", "validation.txt"}
    s = json.loads(z.read("summary.json"))
    assert s["records"] == 2 and s["taxa"] == 2 and s["markers"] == ["12S", "COI"]
    assert s["archive"]["sha256"] == hashlib.sha256(b"PK-fake-archive").hexdigest()
    assert s["bounding_box"]["north"] == 60.1 and s["date_range"] == ["2024-05-01", "2024-05-02"]
    assert z.read("dna_dataset.zip") == b"PK-fake-archive"
    assert "Métadonnées" in z.read("validation.txt").decode()


def test_demo_is_flagged():
    z = _open(demo=True)
    assert "NOT FOR PUBLICATION" in z.read("README.txt").decode()
    assert json.loads(z.read("summary.json"))["demo_data"] is True
