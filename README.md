# DNA Pipeline GBIF (SPLICE)

Pipeline de publication de données ADN dérivées (barcoding, métabarcoding, eDNA)
vers le réseau GBIF, avec interface Streamlit et API GBIF.

## Installation

pip install -e ".[test]"

## Tests

pytest tests/ -m "not integration" -v
pytest tests/integration/ -v

## Utilisation

dna-pipeline run --input-path data/raw/example.csv
streamlit run app/streamlit_app.py

## Déploiement Streamlit Cloud

1. Pousser sur GitHub.
2. Connecter sur https://share.streamlit.io avec `app/streamlit_app.py` comme fichier principal.
