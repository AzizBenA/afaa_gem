import importlib
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from cobra import Reaction
from matplotlib import pyplot as plt

from afaa import phpp as public_phpp
from afaa.phpp import (
    PhppResult,
    analyze_phpp,
    compute_phpp,
    fit_linear_regression,
    group_experimental_data,
)
from afaa.workbench import Workbench


phpp_module = importlib.import_module("afaa.phpp")


@pytest.fixture
def envelope():
    return pd.DataFrame(
        {
            "EX_h2_e": [-2.0, -2.0, -4.0, -4.0],
            "EX_o2_e": [-1.0, -2.0, -2.0, -3.0],
            "flux_maximum": [0.1, 0.2, 0.3, 0.4],
        }
    )


@pytest.fixture
def experimental_data():
    return pd.DataFrame(
        {
            "H2 Flux theoretic": [2.0, 2.0, 2.0, 4.0, 4.0, 4.0],
            "O2 flux theoretic": [1.0, 1.0, 1.0, 2.0, 2.0, 2.0],
        }
    )


def test_public_phpp_api_is_callable():
    assert callable(public_phpp)


def test_group_experimental_data_calculates_std_and_sem():
    data = pd.DataFrame({"measurement": [1.0, 3.0, 5.0, 7.0]})

    grouped = group_experimental_data(data, replicate_count=2)

    assert grouped["measurement"].tolist() == [2.0, 6.0]
    assert grouped["measurement_std"].tolist() == pytest.approx(
        [np.sqrt(2), np.sqrt(2)]
    )
    assert grouped["measurement_sem"].tolist() == pytest.approx(
        [1.0, 1.0]
    )
    assert grouped["measurement_count"].tolist() == [2, 2]


def test_fit_linear_regression_returns_expected_parameters():
    fit = fit_linear_regression(
        np.array([1.0, 2.0, 3.0]),
        np.array([2.0, 4.0, 6.0]),
    )

    assert fit.slope == pytest.approx(2.0)
    assert fit.intercept == pytest.approx(0.0, abs=1e-12)
    assert fit.r_squared == pytest.approx(1.0)


def test_analyze_phpp_returns_structured_results_without_showing(
    envelope,
    experimental_data,
    monkeypatch,
):
    show = Mock()
    monkeypatch.setattr(phpp_module.plt, "show", show)

    result = analyze_phpp(
        envelope,
        experimental_data,
        experimental_h2_column="H2 Flux theoretic",
        experimental_o2_column="O2 flux theoretic",
        show=False,
    )

    assert isinstance(result, PhppResult)
    assert result.optimality_fit.slope == pytest.approx(2.0)
    assert result.optimality_fit.intercept == pytest.approx(-2.0)
    assert result.experimental_fit is not None
    assert result.experimental_fit.slope == pytest.approx(2.0)
    assert result.experimental_fit.r_squared == pytest.approx(1.0)
    assert result.heatmap_values.shape == (2, 3)
    assert result.grouped_experimental_data is not None
    assert len(result.grouped_experimental_data) == 2
    show.assert_not_called()

    plt.close(result.figure)


def test_analyze_phpp_requires_experimental_column_names(
    envelope,
    experimental_data,
):
    with pytest.raises(
        ValueError,
        match="experimental_h2_column",
    ):
        analyze_phpp(envelope, experimental_data)


def test_analyze_phpp_can_save_figure(
    envelope,
    tmp_path,
):
    output_path = tmp_path / "phpp.png"

    result = analyze_phpp(
        envelope,
        output_path=output_path,
    )

    assert output_path.is_file()
    assert output_path.stat().st_size > 0

    plt.close(result.figure)


def test_analyze_phpp_rejects_missing_columns():
    envelope = pd.DataFrame(
        {
            "EX_h2_e": [-1.0, -2.0],
            "flux_maximum": [0.1, 0.2],
        }
    )

    with pytest.raises(KeyError, match="EX_o2_e"):
        analyze_phpp(envelope)


def test_compute_phpp_delegates_to_cobrapy(
    tiny_model,
    monkeypatch,
):
    second_reaction = Reaction("SECOND_RXN")
    tiny_model.add_reactions([second_reaction])
    expected = pd.DataFrame({"flux_maximum": [1.0]})
    production_envelope = Mock(return_value=expected)
    monkeypatch.setattr(
        phpp_module,
        "production_envelope",
        production_envelope,
    )

    result = compute_phpp(
        tiny_model,
        h2_reaction_id="TEST_RXN",
        o2_reaction_id="SECOND_RXN",
        objective="TEST_RXN",
        points=5,
    )

    assert result is expected
    production_envelope.assert_called_once_with(
        tiny_model,
        reactions=["TEST_RXN", "SECOND_RXN"],
        objective="TEST_RXN",
        points=5,
    )


def test_workbench_phpp_uses_stored_model(
    tiny_model,
    monkeypatch,
):
    expected = object()
    run_phpp = Mock(return_value=expected)
    monkeypatch.setattr("afaa.workbench.run_phpp", run_phpp)
    workbench = Workbench(tiny_model)

    result = workbench.phpp(
        h2_reaction_id="H2",
        o2_reaction_id="O2",
        points=10,
    )

    assert result is expected
    run_phpp.assert_called_once_with(
        tiny_model,
        h2_reaction_id="H2",
        o2_reaction_id="O2",
        points=10,
    )


def test_phpp_forwards_custom_experimental_columns(
    tiny_model,
    monkeypatch,
):
    envelope = pd.DataFrame({"flux_maximum": [1.0]})
    expected = object()
    monkeypatch.setattr(
        phpp_module,
        "compute_phpp",
        Mock(return_value=envelope),
    )
    analyze = Mock(return_value=expected)
    monkeypatch.setattr(phpp_module, "analyze_phpp", analyze)

    result = public_phpp(
        tiny_model,
        experimental_h2_column="hydrogen",
        experimental_o2_column="oxygen",
    )

    assert result is expected
    analyze.assert_called_once_with(
        envelope,
        experimental_data=None,
        h2_column="EX_h2_e",
        o2_column="EX_o2_e",
        experimental_h2_column="hydrogen",
        experimental_o2_column="oxygen",
        output_path=None,
        show=False,
    )
