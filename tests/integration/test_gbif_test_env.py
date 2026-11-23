import pytest
import requests

GBIF_TEST_API = "https://api.gbif-test.org/v1"


@pytest.mark.integration
def test_register_on_gbif_test():
    payload = {
        "publishingOrganizationKey": "0a16da09-7719-40de-8d4f-56a15ed52fb6",
        "installationKey": "92d76df5-3de1-4c89-be03-7a17abad962a",
        "type": "OCCURRENCE",
        "title": "Test Pipeline SPLICE",
        "description": "Dataset de test d'intégration.",
        "language": "eng",
        "license": "http://creativecommons.org/publicdomain/zero/1.0/legalcode",
    }
    r = requests.post(f"{GBIF_TEST_API}/dataset", json=payload,
                      auth=("ws_client_demo", "Demo123"), timeout=30)
    assert r.status_code == 201, r.text
    key = r.json()["key"]
    r = requests.post(f"{GBIF_TEST_API}/dataset/{key}/endpoint",
                      json={"type": "DWC_ARCHIVE", "url": "https://example.com/a.zip"},
                      auth=("ws_client_demo", "Demo123"), timeout=30)
    assert r.status_code == 201, r.text
