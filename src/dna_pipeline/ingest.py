import pandas as pd
from pathlib import Path
from typing import Union
import io

def load_data(file_path: Union[str, Path, io.IOBase, object]) -> pd.DataFrame:
    # Cas 1 : Fichier téléversé via Streamlit (en mémoire)
    if hasattr(file_path, "name") and not isinstance(file_path, (str, Path)):
        filename = file_path.name.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Format non supporté : {filename}")
            
    # Cas 2 : Fichier sur le disque dur (ligne de commande)
    else:
        path = Path(file_path)
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        elif path.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        else:
            raise ValueError(f"Format non supporté : {path.suffix}.")
            
    # Normalisation des noms de colonnes
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df
