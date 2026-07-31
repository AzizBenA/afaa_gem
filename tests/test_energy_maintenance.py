import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from cobra import Metabolite, Model, Reaction

from afaa import optimize_energy_maintenance as public_optimizer
from afaa.energy_maintenance import (
    EnergyMaintenanceResult,
    calculate_difference_for_gam,
    compute_growth_rates,
    compute_mean_difference,
    compute_r2_score,
    estimate_ngam,
    optimize_energy_maintenance,
    set_gam,
)
from afaa.workbench import Workbench


maintenance_module = importlib.import_module("afaa.energy_maintenance")


@pytest.fixture
def maintenance_model():
    model = Model("maintenance_model")

    metabolites = {
        metabolite_id: Metabolite(metabolite_id, compartment="c")
        for metabolite_id in [
            "atp_c",
            "h2o_c",
            "adp_c",
            "pi_c",
            "h_c",
        ]
    }
    growth = Reaction("Growth")
    growth.add_metabolites(
        {
            metabolites["atp_c"]: -10.0,
            metabolites["h2o_c"]: -10.0,
            metabolites["adp_c"]: 10.0,
            metabolites["pi_c"]: 10.0,
            metabolites["h_c"]: 10.0,
        }
    )

    reactions = [
        growth,
        Reaction("ATPM"),
        Reaction("EX_h2_e"),
        Reaction("EX_o2_e"),
        Reaction("EX_co2_e"),
    ]
    model.add_reactions(reactions)
    model.reactions.ATPM.bounds = (0.0, 1000.0)
    return model


@pytest.fixture
def experimental_data():
    return pd.DataFrame(
        {
            "dilRate": [2.0, 4.0, 6.0],
            "H2 Flux theoretic": [2.0, 4.0, 6.0],
        }
    )


def _install_growth_optimizer(model, monkeypatch):
    def optimize():
        h2_flux = model.reactions.EX_h2_e.lower_bound
        growth = -h2_flux
        return SimpleNamespace(
            status="optimal",
            objective_value=growth,
            fluxes=pd.Series(
                {
                    "EX_h2_e": h2_flux,
                    "EX_o2_e": -growth / 2,
                    "EX_co2_e": 0.0,
                }
            ),
        )

    monkeypatch.setattr(model, "optimize", optimize)


def test_public_optimizer_is_callable():
    assert callable(public_optimizer)


def test_error_metrics():
    data = pd.DataFrame(
        {
            "dilRate": [1.0, 2.0, 3.0],
            "growth_rate": [1.0, 2.0, 3.0],
        }
    )

    assert compute_mean_difference(
        data,
        experimental_column="dilRate",
    ) == pytest.approx(0.0)
    assert compute_r2_score(
        data,
        experimental_column="dilRate",
    ) == pytest.approx(1.0)


def test_set_gam_replaces_absolute_coefficients(maintenance_model):
    set_gam(maintenance_model, 25.0)
    growth = maintenance_model.reactions.Growth

    assert growth.get_coefficient("atp_c") == pytest.approx(-25.0)
    assert growth.get_coefficient("h2o_c") == pytest.approx(-25.0)
    assert growth.get_coefficient("adp_c") == pytest.approx(25.0)
    assert growth.get_coefficient("pi_c") == pytest.approx(25.0)
    assert growth.get_coefficient("h_c") == pytest.approx(25.0)


def test_compute_growth_rates_returns_copy_and_restores_model(
    maintenance_model,
    experimental_data,
    monkeypatch,
):
    _install_growth_optimizer(maintenance_model, monkeypatch)
    original_bounds = maintenance_model.reactions.EX_h2_e.bounds

    result = compute_growth_rates(
        maintenance_model,
        experimental_data,
        experimental_h2_column="H2 Flux theoretic",
    )

    assert "growth_rate" not in experimental_data.columns
    assert result["growth_rate"].tolist() == [2.0, 4.0, 6.0]
    assert result["H2 Flux model"].tolist() == [-2.0, -4.0, -6.0]
    assert maintenance_model.reactions.EX_h2_e.bounds == original_bounds


def test_calculate_difference_for_gam_restores_coefficients(
    maintenance_model,
    experimental_data,
    monkeypatch,
):
    _install_growth_optimizer(maintenance_model, monkeypatch)
    original_coefficient = (
        maintenance_model.reactions.Growth.get_coefficient("atp_c")
    )

    mean_difference, r2_score = calculate_difference_for_gam(
        maintenance_model,
        experimental_data,
        30.0,
        experimental_growth_column="dilRate",
        experimental_h2_column="H2 Flux theoretic",
    )

    assert mean_difference == pytest.approx(0.0)
    assert r2_score == pytest.approx(1.0)
    assert (
        maintenance_model.reactions.Growth.get_coefficient("atp_c")
        == original_coefficient
    )


def test_maintenance_accepts_custom_experimental_column_names(
    maintenance_model,
    experimental_data,
    monkeypatch,
):
    _install_growth_optimizer(maintenance_model, monkeypatch)
    renamed = experimental_data.rename(
        columns={
            "dilRate": "measured_growth",
            "H2 Flux theoretic": "hydrogen_uptake",
        }
    )

    mean_difference, r2_score = calculate_difference_for_gam(
        maintenance_model,
        renamed,
        30.0,
        experimental_growth_column="measured_growth",
        experimental_h2_column="hydrogen_uptake",
    )

    assert mean_difference == pytest.approx(0.0)
    assert r2_score == pytest.approx(1.0)


def test_estimate_ngam_restores_model(
    maintenance_model,
    monkeypatch,
):
    original_bounds = maintenance_model.reactions.EX_h2_e.bounds
    original_objective = maintenance_model.objective.expression
    solution = SimpleNamespace(status="optimal", objective_value=7.5)
    monkeypatch.setattr(
        maintenance_model,
        "optimize",
        Mock(return_value=solution),
    )

    result = estimate_ngam(maintenance_model, 10.0)

    assert result == pytest.approx(7.5)
    assert maintenance_model.reactions.EX_h2_e.bounds == original_bounds
    assert maintenance_model.objective.expression == original_objective


def test_optimize_energy_maintenance_selects_best_combination(
    maintenance_model,
    experimental_data,
    tmp_path,
    monkeypatch,
):
    def calculate_difference(model, data, gam_value, **kwargs):
        ngam = model.reactions.ATPM.lower_bound
        error = abs(gam_value - 20.0) + abs(ngam - 2.0)
        return error, 1.0 - error

    monkeypatch.setattr(
        maintenance_module,
        "calculate_difference_for_gam",
        calculate_difference,
    )
    renamed = experimental_data.rename(
        columns={
            "dilRate": "measured_growth",
            "H2 Flux theoretic": "hydrogen_uptake",
        }
    )
    output_path = tmp_path / "maintenance.csv"
    original_atpm_bounds = maintenance_model.reactions.ATPM.bounds

    result = optimize_energy_maintenance(
        maintenance_model,
        renamed,
        gam_values=[10.0, 20.0],
        ngam_values=[1.0, 2.0],
        experimental_growth_column="measured_growth",
        experimental_h2_column="hydrogen_uptake",
        output_path=output_path,
    )

    assert isinstance(result, EnergyMaintenanceResult)
    assert len(result.combinations) == 4
    assert result.best_by_mean_difference.gam == pytest.approx(20.0)
    assert result.best_by_mean_difference.ngam == pytest.approx(2.0)
    assert result.best_by_r2.gam == pytest.approx(20.0)
    assert result.best_by_r2.ngam == pytest.approx(2.0)
    assert output_path.is_file()
    assert maintenance_model.reactions.ATPM.bounds == original_atpm_bounds


def test_workbench_optimizer_uses_stored_model(
    maintenance_model,
    experimental_data,
    monkeypatch,
):
    expected = object()
    optimizer = Mock(return_value=expected)
    monkeypatch.setattr(
        "afaa.workbench.optimize_energy_maintenance",
        optimizer,
    )
    workbench = Workbench(maintenance_model)

    result = workbench.optimize_energy_maintenance(
        experimental_data,
        [10.0, 20.0],
        ngam_values=[1.0, 2.0],
        experimental_growth_column="dilRate",
        experimental_h2_column="H2 Flux theoretic",
    )

    assert result is expected
    optimizer.assert_called_once_with(
        maintenance_model,
        experimental_data,
        [10.0, 20.0],
        ngam_values=[1.0, 2.0],
        experimental_growth_column="dilRate",
        experimental_h2_column="H2 Flux theoretic",
    )
