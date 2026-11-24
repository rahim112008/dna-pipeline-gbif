"""Table OTU/ASV (metabarcoding / eDNA) -> tableau plat au format d'entrée du pipeline."""
import pandas as pd
from .transform import make_occurrence_id


def expand_otu_table(otu: pd.DataFrame, samples: pd.DataFrame, seqs: dict, tax: pd.DataFrame | None = None,
                     id_prefix: str = "dataset") -> pd.DataFrame:
    """otu : OTU (lignes) x échantillons (colonnes) = nombre de reads ; samples : colonne sampleID + lat/lon/date…
    tax : index = OTU, colonne scientific_name (+ kingdom, phylum, class, order, family, genus facultatifs).
    Une ligne par présence (reads > 0), avec occurrenceID stable (hash de la séquence)."""
    long = otu.where(otu > 0).stack().rename("reads").reset_index()
    long.columns = ["otu_id", "sampleID", "reads"]
    long["reads"] = long["reads"].astype(int)
    long["sequence"] = long["otu_id"].map(seqs)
    out = long.merge(samples.rename(columns={"sampleID": "sampleID"}), on="sampleID", how="left")
    if tax is not None:
        out = out.merge(tax.reset_index().rename(columns={tax.index.name or "index": "otu_id"}), on="otu_id", how="left")
    if "scientific_name" not in out:
        out["scientific_name"] = "Biota"
    out["scientific_name"] = out["scientific_name"].fillna("Biota").replace("", "Biota")
    out["sample_name"] = out["sampleID"]
    out["occurrence_id"] = [make_occurrence_id(id_prefix, s, q if isinstance(q, str) else o)
                            for s, q, o in zip(out["sampleID"], out["sequence"], out["otu_id"])]
    out["organismQuantityType"] = "DNA sequence reads"
    return out.drop(columns=["sampleID"])
