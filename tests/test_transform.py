import pandas as pd
import pytest
from dna_pipeline.transform import map_to_dwc


def test_map_renames_columns():
    df = pd.DataFrame({"occurrence_id": ["A"], "lat": [45.0], "target_gene": ["COI"]})
    result = map_to_dwc(df)
    assert "occurrenceID" in result.columns
    assert "decimalLatitude" in result.columns


def test_missing_occurrence_id_raises():
    df = pd.DataFrame({"lat": [45.0]})
    with pytest.raises(ValueError):
        map_to_dwc(df)
