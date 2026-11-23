from pydantic import BaseModel, Field
from typing import Optional


class DNARecord(BaseModel):
    occurrenceID: str = Field(..., description="Identifiant unique et stable")
    scientificName: Optional[str] = None
    decimalLatitude: Optional[float] = None
    decimalLongitude: Optional[float] = None
    eventDate: Optional[str] = None
    target_gene: Optional[str] = None
    seq_meth: Optional[str] = None
    pcr_primer_forward: Optional[str] = None
    pcr_primer_reverse: Optional[str] = None
    dna_sequence: Optional[str] = None
    taxon_id: Optional[str] = None
    samp_name: Optional[str] = None
    project_name: Optional[str] = None
    env_broad_scale: Optional[str] = None
    env_local_scale: Optional[str] = None
    env_medium: Optional[str] = None
