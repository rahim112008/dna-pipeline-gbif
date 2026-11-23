import pandas as pd
from pathlib import Path
from typing import Union


def load_data(file_path: Union[str, Path]) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Format non supporté : {path.suffix}.")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df
