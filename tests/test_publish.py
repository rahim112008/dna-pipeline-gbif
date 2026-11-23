import pandas as pd
from dna_pipeline.publish import generate_dwca


def test_generate_dwca(tmp_path):
    df = pd.DataFrame({
        "occurrenceID": ["A"],
        "scientificName": ["Gadus morhua"],
        "target_gene": ["COI"],
        "dna_sequence": ["ACGT"],
    })
    path = generate_dwca(df, tmp_path)
    assert path.exists() and path.suffix == ".zip"
