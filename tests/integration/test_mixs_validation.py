import pandas as pd
from dna_pipeline.validate import validate_mixs_terms


def test_valid_terms():
    df = pd.DataFrame({"occurrenceID": ["A"], "target_gene": ["COI"],
                        "seq_meth": ["Illumina"], "samp_name": ["S1"],
                        "dna_sequence": ["ACGT"], "project_name": ["P1"]})
    assert validate_mixs_terms(df)["valid"]


def test_invalid_term():
    df = pd.DataFrame({"occurrenceID": ["A"], "colonne_inconnue": ["x"]})
    r = validate_mixs_terms(df)
    assert not r["valid"] and "colonne_inconnue" in r["invalid_terms"]
