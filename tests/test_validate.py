import pandas as pd
from dna_pipeline.validate import validate_dwc


def test_duplicate_occurrence_id():
    df = pd.DataFrame({"occurrenceID": ["A", "A"], "dna_sequence": ["ACGT", "ACGT"]})
    assert any(e["type"] == "Duplication" for e in validate_dwc(df)["errors"])


def test_invalid_dna_sequence():
    df = pd.DataFrame({"occurrenceID": ["A"], "dna_sequence": ["ACGTX"]})
    assert any(e["type"] == "Séquence ADN" for e in validate_dwc(df)["errors"])


def test_valid_dataframe():
    df = pd.DataFrame({"occurrenceID": ["A"], "dna_sequence": ["ACGT"]})
    assert not validate_dwc(df)["errors"]
