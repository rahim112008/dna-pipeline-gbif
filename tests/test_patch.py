import sys
import types
import zipfile
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from dna_pipeline import publish, validate
from dna_pipeline.eml import DatasetMeta, build_eml, validate_meta
from dna_pipeline.metabarcoding import expand_otu_table
from dna_pipeline.transform import map_to_dwc, make_occurrence_id

EX = Path(__file__).parents[1] / "data" / "raw" / "example.csv"
META = DatasetMeta(title="Test", abstract="x" * 60, prefix="t",
                   creators=[{"first_name": "A", "last_name": "B", "email": "a.b@univ-tlemcen.dz"}])


@pytest.fixture
def df():
    return map_to_dwc(pd.read_csv(EX))


def test_map_to_dwc_keeps_legacy_behaviour(df):
    assert df.columns[0] == "occurrenceID" and "dna_sequence" in df.columns and "taxon_id" in df.columns


def test_ids_generated_when_missing():
    raw = pd.read_csv(EX).drop(columns="occurrence_id")
    out = map_to_dwc(raw, id_prefix="sea")
    assert out["occurrenceID"].is_unique and out["occurrenceID"].iloc[0].startswith("sea:S001:")
    with pytest.raises(ValueError):
        map_to_dwc(raw)


def test_valid_example_has_no_errors(df):
    assert validate.validate_dwc(df)["errors"] == []


def test_iupac_accepted_missing_and_bad_rejected(df):
    df.loc[0, "dna_sequence"] = "ACGTRYKMN"
    assert validate.validate_dwc(df)["errors"] == []
    df.loc[1, "dna_sequence"] = None
    df["eventDate"] = ["2024-05-01", "01/05/2024"]
    df.loc[0, "decimalLatitude"] = "6O.1"
    kinds = {(e["type"], e["message"][:12]) for e in validate.validate_dwc(df)["errors"]}
    assert any(t == "Séquence ADN" for t, _ in kinds) and any(t == "Date" for t, _ in kinds)
    assert any(t == "Coordonnées" for t, _ in kinds)           # plus de TypeError sur colonne texte


def test_spec_parser_handles_default_namespace(tmp_path):
    xml = (b'<extension xmlns="http://rs.gbif.org/extension/"><property name="DNA_sequence" '
           b'qualName="http://rs.gbif.org/terms/dna_sequence"/><property name="target_gene" qualName="q2"/></extension>')
    with mock.patch("requests.get", return_value=mock.Mock(content=xml, raise_for_status=lambda: None)), \
         mock.patch.object(validate, "CACHE_DIR", tmp_path):
        assert set(validate.load_mixs_terms_from_spec("http://x", use_cache=False)) == {"DNA_sequence", "target_gene"}
        r = validate.validate_mixs_terms(pd.DataFrame(columns=["occurrenceID", "dna_sequence", "target_gene", "taxon_id"]), "http://y")
    assert r["invalid_terms"] == ["taxon_id"]                  # dna_sequence reconnu via DNA_sequence ; taxon_id absent de la spec


def test_tables_for_archive(df):
    core, ext = publish._prepare_tables(df)
    assert (core["basisOfRecord"] == "MaterialSample").all() and "taxonID" in core.columns
    assert "DNA_sequence" in ext.columns and "dna_sequence" not in ext.columns and "taxon_id" not in ext.columns


def test_generate_dwca_passes_spec_terms(tmp_path, df):
    calls = {}

    class T:
        def __init__(self, **kw): calls.setdefault("tables", []).append(kw)

    class A:
        def __init__(self): self.extensions = []
        def export(self, p): calls["exported"] = p; Path(p).write_bytes(b"zip")
    stub = types.SimpleNamespace(Archive=A, Table=T)
    with mock.patch.dict(sys.modules, {"dwcawriter": stub}):
        out = publish.generate_dwca(df, tmp_path, META)
    core, ext = calls["tables"]
    assert "basisOfRecord" in core["data"].columns and "DNA_sequence" in ext["data"].columns
    assert out.exists()
    with mock.patch.dict(sys.modules, {"dwcawriter": stub}), pytest.raises(ValueError):
        publish.generate_dwca(df, tmp_path, DatasetMeta(title="", creators=[]))


def test_eml_is_well_formed_xml():
    import xml.dom.minidom as m
    e = build_eml(META, pd.DataFrame({"decimalLatitude": [60.1], "decimalLongitude": [5.2], "eventDate": ["2024-05-01"]}))
    m.parseString(e.encode())
    assert "<intellectualRights>" in e and validate_meta(META) == []
    assert validate_meta(DatasetMeta(creators=[{"last_name": "X", "email": "chercheur@exemple.org"}]))


def _resp(code, payload=None, headers=None):
    r = mock.Mock(status_code=code, headers=headers or {}, text=str(payload))
    r.json.return_value = payload
    return r


def test_api_final_429_raises_instead_of_returning_none():
    with mock.patch("requests.request", return_value=_resp(429)), mock.patch("time.sleep"):
        with pytest.raises(RuntimeError):
            publish.gbif_api_call("GET", "http://x", max_retries=3)


def test_api_4xx_not_retried():
    with mock.patch("requests.request", return_value=_resp(401, "no")) as m:
        with pytest.raises(publish.GBIFError):
            publish.gbif_api_call("POST", "http://x")
    assert m.call_count == 1


@pytest.mark.parametrize("body", ["abc-123", {"key": "abc-123"}])
def test_register_accepts_string_or_object_key(monkeypatch, body):
    monkeypatch.setenv("GBIF_USER", "u"); monkeypatch.setenv("GBIF_PWD", "p")
    seen = []
    def fake(method, url, **kw):
        seen.append(url); return _resp(200, body if url.endswith("/dataset") else {})
    with mock.patch("dna_pipeline.publish.gbif_api_call", side_effect=fake):
        assert publish.register_dataset_with_gbif({}, "https://h.org/a.zip") == "abc-123"
    assert "gbif-uat" in seen[0]                                # UAT par défaut


def test_otu_table_expansion_roundtrip():
    otu = pd.DataFrame({"S1": [10, 0], "S2": [5, 7]}, index=["o1", "o2"])
    samples = pd.DataFrame({"sampleID": ["S1", "S2"], "latitude": [1, 2], "longitude": [3, 4], "event_date": ["2025-01-01"] * 2})
    flat = expand_otu_table(otu, samples, {"o1": "ACGT", "o2": "TTGA"}, id_prefix="m")
    assert len(flat) == 3
    out = map_to_dwc(flat.rename(columns={"reads": "organismQuantity"}))
    assert out["occurrenceID"].is_unique and validate.validate_dwc(out)["errors"] == []
    assert make_occurrence_id("m", "S1", "ACGT") in set(out["occurrenceID"])
