from unittest.mock import Mock

from afaa.bigg import BiggClient
from afaa.curation import (
    find_bigg_reference_models,
    update_metabolite_charges_from_bigg,
)


def test_find_bigg_reference_models(monkeypatch, tiny_model):
    reaction = tiny_model.reactions.get_by_id("TEST_RXN")

    monkeypatch.setattr(
        "afaa.curation.cobra.manipulation.validate.check_mass_balance",
        lambda model: {reaction: {"C": -1}},
    )

    client = Mock(spec=BiggClient)
    client.get_reaction.return_value = {
        "models_containing_reaction": [
            {"bigg_id": "reference_model"}
        ]
    }

    result = find_bigg_reference_models(
        tiny_model,
        client,
        verbose=False,
    )

    assert result == {"TEST_RXN": "reference_model"}
    client.get_reaction.assert_called_once_with("TEST_RXN")


def test_find_bigg_reference_models_honors_limit(
    monkeypatch,
    tiny_model,
):
    reaction = tiny_model.reactions.get_by_id("TEST_RXN")

    monkeypatch.setattr(
        "afaa.curation.cobra.manipulation.validate.check_mass_balance",
        lambda model: {reaction: {"C": -1}},
    )

    client = Mock(spec=BiggClient)

    result = find_bigg_reference_models(
        tiny_model,
        client,
        limit=0,
        verbose=False,
    )

    assert result == {}
    client.get_reaction.assert_not_called()


def test_update_zero_charge_from_bigg(tiny_model):
    metabolite = tiny_model.metabolites.get_by_id("substrate_c")
    assert metabolite.charge == 0

    client = Mock(spec=BiggClient)
    client.get_metabolite.return_value = {"charge": -1}

    updated = update_metabolite_charges_from_bigg(
        tiny_model,
        client,
        {"TEST_RXN": "reference_model"},
    )

    assert metabolite.charge == -1
    assert updated >= 1
    client.get_metabolite.assert_any_call(
        model_id="reference_model",
        metabolite_id="substrate_c",
    )