from unittest.mock import Mock

import pytest
import requests

from afaa.bigg import BiggClient


def test_get_reaction_returns_decoded_json():
    session = Mock()
    response = session.get.return_value
    response.json.return_value = {
        "bigg_id": "PGI",
        "models_containing_reaction": [],
    }

    client = BiggClient(
        base_url="https://example.test/api/v2/",
        timeout=5,
        session=session,
    )

    result = client.get_reaction("PGI")

    assert result["bigg_id"] == "PGI"
    session.get.assert_called_once_with(
        "https://example.test/api/v2/universal/reactions/PGI",
        timeout=5,
    )
    response.raise_for_status.assert_called_once_with()


def test_get_metabolite_returns_decoded_json():
    session = Mock()
    response = session.get.return_value
    response.json.return_value = {
        "bigg_id": "atp_c",
        "charge": -4,
    }

    client = BiggClient(session=session)

    result = client.get_metabolite("iJO1366", "atp_c")

    assert result["charge"] == -4
    session.get.assert_called_once_with(
        (
            "http://bigg.ucsd.edu/api/v2/"
            "models/iJO1366/metabolites/atp_c"
        ),
        timeout=15,
    )


def test_get_reaction_propagates_http_error():
    session = Mock()
    session.get.return_value.raise_for_status.side_effect = (
        requests.HTTPError("BiGG request failed")
    )

    client = BiggClient(session=session)

    with pytest.raises(requests.HTTPError):
        client.get_reaction("UNKNOWN")