import matplotlib
import pytest
from cobra import Metabolite, Model, Reaction


matplotlib.use("Agg")


@pytest.fixture
def tiny_model():
    model = Model("tiny_model")

    substrate = Metabolite(
        "substrate_c",
        name="Substrate",
        formula="C",
        charge=0,
        compartment="c",
    )
    product = Metabolite(
        "product_c",
        name="Product",
        formula="C",
        charge=0,
        compartment="c",
    )

    reaction = Reaction("TEST_RXN")
    reaction.name = "Test reaction"
    reaction.lower_bound = 0
    reaction.upper_bound = 1000
    reaction.add_metabolites(
        {
            substrate: -1,
            product: 1,
        }
    )

    model.add_reactions([reaction])
    return model
