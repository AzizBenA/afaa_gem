import pytest
from cobra import Model
from cobra.io import write_sbml_model
from cobra import Metabolite, Model, Reaction
from afaa.model_io import load_sbml_model




def test_load_sbml_model(tiny_model, tmp_path):
    model_path = tmp_path / "model.xml"
    write_sbml_model(tiny_model, str(model_path))

    loaded = load_sbml_model(model_path)

    assert isinstance(loaded, Model)
    assert loaded.id == tiny_model.id
    assert {r.id for r in loaded.reactions} == {
        r.id for r in tiny_model.reactions
    }


def test_load_missing_model_raises_error(tmp_path):
    missing_path = tmp_path / "missing.xml"

    with pytest.raises(FileNotFoundError):
        load_sbml_model(missing_path)