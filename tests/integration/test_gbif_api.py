from unittest.mock import patch, Mock
from dna_pipeline.publish import gbif_api_call, register_dataset_with_gbif


@patch("requests.request")
def test_retry_on_429(mock_request):
    mock_429 = Mock(status_code=429)
    mock_200 = Mock(status_code=200)
    mock_200.json.return_value = {"key": "abc"}
    mock_request.side_effect = [mock_429, mock_429, mock_200]
    resp = gbif_api_call("POST", "https://api.gbif-test.org/v1/dataset", auth=("u", "p"))
    assert resp.status_code == 200


@patch("requests.request")
def test_register_does_two_calls(mock_request):
    mock_create = Mock(status_code=201)
    mock_create.json.return_value = {"key": "new-key"}
    mock_endpoint = Mock(status_code=201)
    mock_request.side_effect = [mock_create, mock_endpoint]
    with patch.dict("os.environ", {"GBIF_USER": "u", "GBIF_PWD": "p"}):
        key = register_dataset_with_gbif({"title": "t"}, "https://example.com/a.zip",
                                          api_base="https://api.gbif-test.org/v1")
    assert key == "new-key"
