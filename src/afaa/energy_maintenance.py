"""Calibration of growth- and non-growth-associated maintenance energy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TypeAlias

import numpy as np
import pandas as pd
from cobra import Model


PathLike: TypeAlias = str | Path


@dataclass(frozen=True)
class MaintenanceCandidate:
    """One evaluated GAM/NGAM parameter combination."""

    gam: float
    ngam: float
    mean_difference: float
    r2_score: float
    h2_uptake_basis: float | None = None


@dataclass
class EnergyMaintenanceResult:
    """Results and best candidates from an energy-maintenance search."""

    combinations: pd.DataFrame
    best_by_mean_difference: MaintenanceCandidate
    best_by_r2: MaintenanceCandidate


def _require_columns(
    dataframe: pd.DataFrame,
    columns: set[str],
) -> None:
    missing = columns - set(dataframe.columns)
    if missing:
        raise KeyError(
            f"Missing required experimental columns: {sorted(missing)}"
        )


def _as_numeric_values(
    values: Iterable[float],
    *,
    name: str,
) -> list[float]:
    converted = [float(value) for value in values]
    if not converted:
        raise ValueError(f"{name} must contain at least one value.")
    if not np.isfinite(converted).all():
        raise ValueError(f"{name} must contain only finite values.")
    if any(value < 0 for value in converted):
        raise ValueError(f"{name} must not contain negative values.")
    return converted


def _candidate_from_row(row: pd.Series) -> MaintenanceCandidate:
    h2_uptake_basis = row.get("H2_uptake_basis")
    if pd.isna(h2_uptake_basis):
        h2_uptake_basis = None

    return MaintenanceCandidate(
        gam=float(row["GAM_value"]),
        ngam=float(row["NGAM_value"]),
        mean_difference=float(row["Mean_Difference"]),
        r2_score=float(row["R2_Score"]),
        h2_uptake_basis=(
            None
            if h2_uptake_basis is None
            else float(h2_uptake_basis)
        ),
    )


def compute_r2_score(
    data: pd.DataFrame,
    *,
    experimental_column: str,
    simulated_column: str = "growth_rate",
) -> float:
    """Calculate R-squared between experimental and simulated growth."""
    _require_columns(
        data,
        {experimental_column, simulated_column},
    )
    clean = data[[experimental_column, simulated_column]].apply(
        pd.to_numeric,
        errors="coerce",
    ).dropna()

    if len(clean) < 2:
        raise ValueError(
            "At least two valid experimental/simulated pairs are required."
        )

    observed = clean[experimental_column].to_numpy(dtype=float)
    predicted = clean[simulated_column].to_numpy(dtype=float)
    residual_sum = float(np.sum((observed - predicted) ** 2))
    total_sum = float(np.sum((observed - observed.mean()) ** 2))

    if np.isclose(total_sum, 0.0):
        return 1.0 if np.isclose(residual_sum, 0.0) else 0.0
    return 1.0 - residual_sum / total_sum


def compute_mean_difference(
    data: pd.DataFrame,
    *,
    experimental_column: str,
    simulated_column: str = "growth_rate",
) -> float:
    """Calculate mean absolute growth-rate error."""
    _require_columns(
        data,
        {experimental_column, simulated_column},
    )
    clean = data[[experimental_column, simulated_column]].apply(
        pd.to_numeric,
        errors="coerce",
    ).dropna()

    if clean.empty:
        raise ValueError(
            "At least one valid experimental/simulated pair is required."
        )

    return float(
        (
            clean[experimental_column]
            - clean[simulated_column]
        ).abs().mean()
    )


def set_gam(
    model: Model,
    gam_value: float,
    *,
    biomass_reaction_id: str = "Growth",
    atp_id: str = "atp_c",
    water_id: str = "h2o_c",
    adp_id: str = "adp_c",
    phosphate_id: str = "pi_c",
    proton_id: str = "h_c",
) -> None:
    """Set absolute GAM coefficients on a biomass reaction in place."""
    gam = float(gam_value)
    if not np.isfinite(gam) or gam < 0:
        raise ValueError("gam_value must be a finite non-negative value.")

    reaction = model.reactions.get_by_id(biomass_reaction_id)
    coefficients = {
        atp_id: -gam,
        water_id: -gam,
        adp_id: gam,
        phosphate_id: gam,
        proton_id: gam,
    }

    metabolites = {}
    for metabolite_id, coefficient in coefficients.items():
        metabolite = model.metabolites.get_by_id(metabolite_id)
        if metabolite not in reaction.metabolites:
            raise KeyError(
                f"Metabolite '{metabolite_id}' is not part of biomass "
                f"reaction '{biomass_reaction_id}'."
            )
        metabolites[metabolite] = coefficient

    reaction.add_metabolites(metabolites, combine=False)


def compute_growth_rates(
    model: Model,
    experimental_data: pd.DataFrame,
    *,
    experimental_h2_column: str,
    objective_reaction_id: str = "Growth",
    h2_reaction_id: str = "EX_h2_e",
    o2_reaction_id: str = "EX_o2_e",
    co2_reaction_id: str = "EX_co2_e",
    unrestricted_uptake: float = 100.0,
) -> pd.DataFrame:
    """Simulate growth for each experimental hydrogen uptake condition.

    A copy of the input DataFrame is returned. Objective and reaction bounds
    are restored when the calculation finishes.
    """
    _require_columns(experimental_data, {experimental_h2_column})
    if unrestricted_uptake <= 0:
        raise ValueError("unrestricted_uptake must be positive.")

    result = experimental_data.copy()
    h2_values = pd.to_numeric(
        result[experimental_h2_column],
        errors="coerce",
    )
    if h2_values.isna().any() or (h2_values < 0).any():
        raise ValueError(
            f"Column '{experimental_h2_column}' must contain finite "
            "non-negative uptake values."
        )

    result["growth_rate"] = np.nan
    result["H2 Flux model"] = np.nan
    result["O2 Flux model"] = np.nan
    result["CO2 Flux model"] = np.nan

    with model:
        model.objective = objective_reaction_id
        h2_reaction = model.reactions.get_by_id(h2_reaction_id)
        o2_reaction = model.reactions.get_by_id(o2_reaction_id)
        co2_reaction = model.reactions.get_by_id(co2_reaction_id)

        for index, uptake in h2_values.items():
            h2_reaction.bounds = (-float(uptake), 0.0)
            o2_reaction.bounds = (-unrestricted_uptake, 0.0)
            co2_reaction.bounds = (-unrestricted_uptake, 0.0)

            solution = model.optimize()
            if solution.status != "optimal":
                continue

            result.at[index, "growth_rate"] = solution.objective_value
            result.at[index, "H2 Flux model"] = solution.fluxes[
                h2_reaction_id
            ]
            result.at[index, "O2 Flux model"] = solution.fluxes[
                o2_reaction_id
            ]
            result.at[index, "CO2 Flux model"] = solution.fluxes[
                co2_reaction_id
            ]

    return result


def estimate_ngam(
    model: Model,
    h2_uptake: float,
    *,
    atpm_reaction_id: str = "ATPM",
    h2_reaction_id: str = "EX_h2_e",
    atpm_upper_bound: float = 1000.0,
) -> float:
    """Estimate maximum ATP maintenance at a fixed H2 uptake rate."""
    uptake = float(h2_uptake)
    if not np.isfinite(uptake) or uptake < 0:
        raise ValueError(
            "h2_uptake must be a finite non-negative value."
        )
    if atpm_upper_bound <= 0:
        raise ValueError("atpm_upper_bound must be positive.")

    with model:
        h2_reaction = model.reactions.get_by_id(h2_reaction_id)
        atpm_reaction = model.reactions.get_by_id(atpm_reaction_id)
        h2_reaction.bounds = (-uptake, 0.0)
        atpm_reaction.bounds = (0.0, atpm_upper_bound)
        model.objective = atpm_reaction_id

        solution = model.optimize()
        if solution.status != "optimal":
            raise RuntimeError(
                "Unable to estimate NGAM: ATPM optimization was not optimal."
            )
        return float(solution.objective_value)


def calculate_difference_for_gam(
    model: Model,
    experimental_data: pd.DataFrame,
    gam_value: float,
    *,
    experimental_growth_column: str,
    experimental_h2_column: str,
    biomass_reaction_id: str = "Growth",
    **growth_options,
) -> tuple[float, float]:
    """Evaluate mean absolute error and R-squared for one GAM value."""
    with model:
        set_gam(
            model,
            gam_value,
            biomass_reaction_id=biomass_reaction_id,
        )
        simulated = compute_growth_rates(
            model,
            experimental_data,
            objective_reaction_id=biomass_reaction_id,
            experimental_h2_column=experimental_h2_column,
            **growth_options,
        )
        mean_difference = compute_mean_difference(
            simulated,
            experimental_column=experimental_growth_column,
        )
        r2_value = compute_r2_score(
            simulated,
            experimental_column=experimental_growth_column,
        )
    return mean_difference, r2_value


def _write_results(
    results: pd.DataFrame,
    output_path: PathLike,
) -> None:
    path = Path(output_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        results.to_csv(path, index=False)
    elif suffix in {".xlsx", ".xls"}:
        results.to_excel(path, index=False)
    else:
        raise ValueError(
            "output_path must use a .csv, .xlsx, or .xls extension."
        )


def optimize_energy_maintenance(
    model: Model,
    experimental_data: pd.DataFrame,
    gam_values: Iterable[float],
    *,
    experimental_growth_column: str,
    experimental_h2_column: str,
    ngam_values: Iterable[float] | None = None,
    h2_uptake_values: Iterable[float] | None = None,
    biomass_reaction_id: str = "Growth",
    atpm_reaction_id: str = "ATPM",
    h2_reaction_id: str = "EX_h2_e",
    o2_reaction_id: str = "EX_o2_e",
    co2_reaction_id: str = "EX_co2_e",
    unrestricted_uptake: float = 100.0,
    output_path: PathLike | None = None,
    verbose: bool = False,
) -> EnergyMaintenanceResult:
    """Find GAM/NGAM combinations that best reproduce measured growth.

    Supply explicit ``ngam_values`` or use ``h2_uptake_values`` to estimate
    maximum ATP-maintenance fluxes at fixed hydrogen uptake rates. Exactly one
    of these arguments must be provided.
    """
    if (ngam_values is None) == (h2_uptake_values is None):
        raise ValueError(
            "Provide exactly one of ngam_values or h2_uptake_values."
        )

    _require_columns(
        experimental_data,
        {experimental_growth_column, experimental_h2_column},
    )
    gam_candidates = _as_numeric_values(
        gam_values,
        name="gam_values",
    )

    maintenance_candidates: list[tuple[float | None, float]] = []
    if ngam_values is not None:
        for ngam in _as_numeric_values(
            ngam_values,
            name="ngam_values",
        ):
            maintenance_candidates.append((None, ngam))
    else:
        assert h2_uptake_values is not None
        uptake_candidates = _as_numeric_values(
            h2_uptake_values,
            name="h2_uptake_values",
        )
        for uptake in uptake_candidates:
            ngam = estimate_ngam(
                model,
                uptake,
                atpm_reaction_id=atpm_reaction_id,
                h2_reaction_id=h2_reaction_id,
            )
            maintenance_candidates.append((uptake, ngam))

    atpm_reaction = model.reactions.get_by_id(atpm_reaction_id)
    rows = []

    for h2_basis, ngam in maintenance_candidates:
        if ngam > atpm_reaction.upper_bound:
            raise ValueError(
                f"NGAM value {ngam} exceeds the upper bound of "
                f"reaction '{atpm_reaction_id}'."
            )

        for gam in gam_candidates:
            with model:
                model.reactions.get_by_id(
                    atpm_reaction_id
                ).lower_bound = ngam
                mean_difference, r2_value = (
                    calculate_difference_for_gam(
                        model,
                        experimental_data,
                        gam,
                        biomass_reaction_id=biomass_reaction_id,
                        experimental_growth_column=(
                            experimental_growth_column
                        ),
                        h2_reaction_id=h2_reaction_id,
                        o2_reaction_id=o2_reaction_id,
                        co2_reaction_id=co2_reaction_id,
                        experimental_h2_column=(
                            experimental_h2_column
                        ),
                        unrestricted_uptake=unrestricted_uptake,
                    )
                )

            row = {
                "H2_uptake_basis": h2_basis,
                "NGAM_value": ngam,
                "GAM_value": gam,
                "Mean_Difference": mean_difference,
                "R2_Score": r2_value,
            }
            rows.append(row)
            if verbose:
                print(
                    f"GAM={gam:g}, NGAM={ngam:g}, "
                    f"MAE={mean_difference:.6g}, R2={r2_value:.6g}"
                )

    combinations = pd.DataFrame(rows)
    valid_mean = combinations["Mean_Difference"].dropna()
    valid_r2 = combinations["R2_Score"].dropna()
    if valid_mean.empty or valid_r2.empty:
        raise RuntimeError(
            "No valid maintenance-parameter scores were produced."
        )

    best_by_mean_difference = _candidate_from_row(
        combinations.loc[valid_mean.idxmin()]
    )
    best_by_r2 = _candidate_from_row(
        combinations.loc[valid_r2.idxmax()]
    )

    if output_path is not None:
        _write_results(combinations, output_path)

    return EnergyMaintenanceResult(
        combinations=combinations,
        best_by_mean_difference=best_by_mean_difference,
        best_by_r2=best_by_r2,
    )


__all__ = [
    "EnergyMaintenanceResult",
    "MaintenanceCandidate",
    "calculate_difference_for_gam",
    "compute_growth_rates",
    "compute_mean_difference",
    "compute_r2_score",
    "estimate_ngam",
    "optimize_energy_maintenance",
    "set_gam",
]
