import io
import sys
import zipfile
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from dna_pipeline import gbif_tools as g
from dna_pipeline.eml import DatasetMeta

UUID = "11111111-2222-3333-4444-555555555555"
META = DatasetMeta(title="T", abstract="x" * 60, creators=[{"last_name": "B", "email": "a@b.dz"}])


def _zip(rows, sep="\t", header=True):
    meta = ('<archive xmlns="http://rs.tdwg.org/dwc/text/"><core encoding="UTF-8" fieldsTerminatedBy="%s" '
            'linesTerminatedBy="\\n" fieldsEnclosedBy="" ignoreHeaderLines="%d" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">'
            '<files><location>occurrence.txt</location></files><id index="0"/>'
            '<field index="0" term="http://rs.tdwg.org/dwc/terms/occurrenceID"/>'
            '<field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/></core></archive>'
            % ("\\t" if sep == "\t" else sep, 1 if header else 0))
    txt = ("occurrenceID%sscientificName\n" % sep if header else "") + "".join(f"{i}{sep}sp\n" for i in rows)
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("meta.xml", meta); z.writestr("occurrence.txt", txt)
    return b.getvalue()


@pytest.mark.parametrize("sep,header", [("\t", True), (",", True), ("\t", False)])
def test_core_ids_any_format(sep, header):
    assert g.core_ids(_zip(["a", "b", "c"], sep, header)) == {"a", "b", "c"}


def test_diff():
    assert g.diff_ids({"a", "b"}, {"b", "c", "d"}) == {"added": 2, "removed": 1, "unchanged": 1}


def _resp(status=200, chunk=b"PK\x03\x04", headers=None, url="http://x/a.zip"):
    r = mock.Mock(status_code=status, headers=headers or {}, url=url)
    r.iter_content.return_value = iter([chunk])
    return r


def test_check_url_ok_and_failures():
    with mock.patch("requests.get", return_value=_resp(headers={"Content-Length": "123"})):
        r = g.check_archive_url("http://x/a.zip"); assert r["ok"] and r["size"] == 123
    with mock.patch("requests.get", return_value=_resp(chunk=b"<!DO")):
        assert not g.check_archive_url("http://x/page")["ok"]
    with mock.patch("requests.get", return_value=_resp(status=404)):
        assert "404" in g.check_archive_url("http://x/none")["message"]
    assert not g.check_archive_url("ftp://x")["ok"]


def test_register_explicit_auth_no_env(monkeypatch):
    monkeypatch.delenv("GBIF_USER", raising=False)
    calls = []

    def fake(method, url, **kw):
        calls.append((method, url, kw.get("auth"), kw.get("json")))
        r = mock.Mock(); r.json.return_value = UUID if url.endswith("/dataset") else {}
        return r
    with mock.patch("dna_pipeline.gbif_tools.gbif_api_call", side_effect=fake):
        key = g.register(META, "https://h/a.zip", UUID, UUID, "uat", "u", "p")
    assert key == UUID and calls[0][2] == ("u", "p") and "gbif-uat" in calls[0][1]
    assert calls[1][3]["type"] == "DWC_ARCHIVE"
    with pytest.raises(ValueError):
        g.register(META, "https://h/a.zip", "pas-un-uuid", UUID, "uat", "u", "p")
    with pytest.raises(ValueError):
        g.register(META, "https://h/a.zip", UUID, UUID, "uat", "", "")
