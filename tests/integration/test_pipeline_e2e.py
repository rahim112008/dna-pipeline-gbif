from dna_pipeline.ingest import load_data
from dna_pipeline.transform import map_to_dwc
from dna_pipeline.validate import validate_dwc, validate_dwca_archive
from dna_pipeline.publish import generate_dwca


def test_full_pipeline(tmp_path):
    df = load_data("data/raw/example.csv")
    df_mapped = map_to_dwc(df)
    assert not validate_dwc(df_mapped)["errors"]
    archive = generate_dwca(df_mapped, tmp_path)
    assert archive.exists()
    assert validate_dwca_archive(archive)
