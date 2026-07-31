"""Phenotype phase plane (PhPP) computation, analysis, and plotting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from cobra import Model
from cobra.flux_analysis import production_envelope
from matplotlib.axes import Axes
from matplotlib.figure import Figure


PathLike: TypeAlias = str | Path
DataSource: TypeAlias = pd.DataFrame | PathLike
ErrorType: TypeAlias = Literal["std", "sem"]


PHPP_STYLE = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "mathtext.fontset": "custom",
    "mathtext.rm": "Arial",
    "mathtext.it": "Arial:italic",
    "mathtext.default": "regular",
    "figure.dpi": 150,
    "savefig.dpi": 600,
    "font.size": 10,
    "axes.labelsize": 12,
    "axes.labelweight": "medium",
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
}


@dataclass(frozen=True)
class LinearFit:
    """Parameters and goodness of fit for a straight line."""

    slope: float
    intercept: float
    r_squared: float | None = None

    def predict(self, values) -> np.ndarray:
        """Evaluate the fitted line for one or more values."""
        array = np.asarray(values, dtype=float)
        return self.slope * array + self.intercept


@dataclass
class PhppResult:
    """Structured output from a phenotype phase plane analysis."""

    envelope: pd.DataFrame
    grouped_experimental_data: pd.DataFrame | None
    optimality_points: pd.DataFrame
    optimality_fit: LinearFit
    experimental_fit: LinearFit | None
    heatmap_x_edges: np.ndarray
    heatmap_y_edges: np.ndarray
    heatmap_values: np.ndarray
    figure: Figure
    axes: Axes


def _load_dataframe(source: DataSource, *, label: str) -> pd.DataFrame:
    if isinstance(source, pd.DataFrame):
        return source.copy()

    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"{label} file does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    raise ValueError(
        f"Unsupported {label} file type '{suffix}'. "
        "Use a CSV or Excel file."
    )


def _require_columns(
    dataframe: pd.DataFrame,
    columns: set[str],
    *,
    label: str,
) -> None:
    missing = columns - set(dataframe.columns)
    if missing:
        raise KeyError(
            f"Missing required {label} columns: {sorted(missing)}"
        )


def _numeric_values(
    dataframe: pd.DataFrame,
    column: str,
    *,
    label: str,
) -> pd.Series:
    try:
        return pd.to_numeric(dataframe[column], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Column '{column}' in {label} must contain numeric values."
        ) from exc


def compute_phpp(
    model: Model,
    h2_reaction_id: str = "EX_h2_e",
    o2_reaction_id: str = "EX_o2_e",
    *,
    objective=None,
    points: int = 20,
) -> pd.DataFrame:
    """Calculate a two-dimensional production envelope with COBRApy.

    Parameters
    ----------
    model:
        COBRA model to analyse.
    h2_reaction_id:
        Reaction ID used for the hydrogen phase-plane axis.
    o2_reaction_id:
        Reaction ID used for the oxygen phase-plane axis.
    objective:
        Optional COBRApy objective. The model's current objective is used when
        omitted.
    points:
        Number of grid points per reaction.
    """
    if points < 2:
        raise ValueError("points must be at least 2.")

    missing = [
        reaction_id
        for reaction_id in (h2_reaction_id, o2_reaction_id)
        if reaction_id not in model.reactions
    ]
    if missing:
        raise KeyError(
            f"Reaction IDs not found in model: {missing}"
        )

    return production_envelope(
        model,
        reactions=[h2_reaction_id, o2_reaction_id],
        objective=objective,
        points=points,
    )


def group_experimental_data(
    experimental_data: pd.DataFrame,
    *,
    replicate_count: int = 3,
    group_column: str | None = None,
) -> pd.DataFrame:
    """Group experimental replicates and calculate mean, SD, SEM, and count.

    When ``group_column`` is omitted, each consecutive ``replicate_count`` rows
    are treated as one condition.
    """
    if replicate_count < 1:
        raise ValueError("replicate_count must be at least 1.")
    if experimental_data.empty:
        raise ValueError("experimental_data must contain at least one row.")

    data = experimental_data.copy()

    if group_column is not None:
        _require_columns(
            data,
            {group_column},
            label="experimental",
        )
        groups = data.groupby(
            group_column,
            sort=False,
            dropna=False,
        )
        means = groups.mean(numeric_only=True)
        standard_deviations = groups.std(numeric_only=True)
        counts = groups.count()
        result = means.reset_index()
        standard_deviations = standard_deviations.reset_index(drop=True)
        counts = counts.reset_index(drop=True)
    else:
        group_ids = np.arange(len(data)) // replicate_count
        groups = data.groupby(group_ids, sort=False)
        means = groups.mean(numeric_only=True)
        standard_deviations = groups.std(numeric_only=True)
        counts = groups.count()
        result = means.reset_index(drop=True)
        standard_deviations = standard_deviations.reset_index(drop=True)
        counts = counts.reset_index(drop=True)

    numeric_columns = list(means.columns)
    if not numeric_columns:
        raise ValueError(
            "experimental_data must contain numeric measurement columns."
        )

    for column in numeric_columns:
        count = counts[column].astype(float)
        standard_deviation = standard_deviations[column].astype(float)
        result[f"{column}_std"] = standard_deviation
        result[f"{column}_sem"] = standard_deviation / np.sqrt(count)
        result[f"{column}_count"] = count.astype(int)

    return result


def calculate_error_for_plotting(
    grouped_data: pd.DataFrame,
    *,
    x_column: str,
    y_column: str,
    error_type: ErrorType = "std",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Extract grouped x/y values and their SD or SEM error arrays."""
    if error_type not in {"std", "sem"}:
        raise ValueError("error_type must be either 'std' or 'sem'.")

    x_error_column = f"{x_column}_{error_type}"
    y_error_column = f"{y_column}_{error_type}"
    _require_columns(
        grouped_data,
        {x_column, y_column, x_error_column, y_error_column},
        label="grouped experimental",
    )

    return (
        grouped_data[x_column].astype(float).to_numpy(),
        grouped_data[y_column].astype(float).to_numpy(),
        grouped_data[x_error_column].astype(float).to_numpy(),
        grouped_data[y_error_column].astype(float).to_numpy(),
    )


def fit_linear_regression(x_values, y_values) -> LinearFit:
    """Fit ``y = slope * x + intercept`` and calculate R-squared."""
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)

    if x.ndim != 1 or y.ndim != 1:
        raise ValueError("Regression inputs must be one-dimensional.")
    if len(x) != len(y):
        raise ValueError("Regression inputs must have equal lengths.")

    finite = np.isfinite(x) & np.isfinite(y)
    x = x[finite]
    y = y[finite]

    if len(x) < 2:
        raise ValueError("At least two finite points are required.")
    if np.unique(x).size < 2:
        raise ValueError(
            "At least two distinct x values are required."
        )

    slope, intercept = np.polyfit(x, y, 1)
    prediction = slope * x + intercept
    residual_sum = float(np.sum((y - prediction) ** 2))
    total_sum = float(np.sum((y - np.mean(y)) ** 2))

    if np.isclose(total_sum, 0.0):
        r_squared = 1.0 if np.isclose(residual_sum, 0.0) else 0.0
    else:
        r_squared = 1.0 - residual_sum / total_sum

    return LinearFit(
        slope=float(slope),
        intercept=float(intercept),
        r_squared=float(r_squared),
    )


def get_exp_linear_regression(
    exp_x,
    exp_y,
) -> tuple[float, float, float]:
    """Return slope, intercept, and R-squared for experimental data."""
    fit = fit_linear_regression(exp_x, exp_y)
    return fit.slope, fit.intercept, float(fit.r_squared)


def _calculate_optimality(
    feasible_data: pd.DataFrame,
    *,
    growth_column: str,
    h2_plot_column: str,
    o2_plot_column: str,
) -> tuple[pd.DataFrame, LinearFit]:
    data = feasible_data.copy()
    data["_h2_round"] = data[h2_plot_column].round(10)
    data["_growth_round"] = data[growth_column].round(5)

    optimality_points = (
        data.assign(
            _maximum_growth=data.groupby("_h2_round")[
                "_growth_round"
            ].transform("max")
        )
        .query("_growth_round == _maximum_growth")
        .sort_values(
            ["_h2_round", o2_plot_column],
            ascending=[True, True],
        )
        .groupby("_h2_round", as_index=False)
        .first()
        .sort_values("_h2_round")
        .drop(
            columns=[
                "_h2_round",
                "_growth_round",
                "_maximum_growth",
            ],
            errors="ignore",
        )
    )

    if len(optimality_points) < 2:
        raise ValueError(
            "At least two optimality points are required to fit a line."
        )

    fit = fit_linear_regression(
        optimality_points[o2_plot_column],
        optimality_points[h2_plot_column],
    )
    return optimality_points, fit


def calculate_optimality_line(
    feasible_data: pd.DataFrame,
    growth_column: str,
    h2_plot_column: str = "x_plot",
    o2_plot_column: str = "y_plot",
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Calculate optimal H2/O2 points and their fitted line."""
    _require_columns(
        feasible_data,
        {growth_column, h2_plot_column, o2_plot_column},
        label="feasible production-envelope",
    )
    points, fit = _calculate_optimality(
        feasible_data,
        growth_column=growth_column,
        h2_plot_column=h2_plot_column,
        o2_plot_column=o2_plot_column,
    )
    return (
        points[h2_plot_column].to_numpy(),
        points[o2_plot_column].to_numpy(),
        fit.slope,
        fit.intercept,
    )


def _centers_to_edges(centers) -> np.ndarray:
    values = np.asarray(centers, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("Heatmap centers must be a non-empty 1D array.")
    if values.size == 1:
        return np.array([values[0] - 0.5, values[0] + 0.5])

    differences = np.diff(values)
    if np.any(differences <= 0):
        raise ValueError(
            "Heatmap centers must be strictly increasing."
        )

    edges = np.empty(values.size + 1)
    edges[1:-1] = values[:-1] + differences / 2
    edges[0] = values[0] - differences[0] / 2
    edges[-1] = values[-1] + differences[-1] / 2
    return edges


def build_heatmap_grid(
    envelope: pd.DataFrame,
    growth_column: str,
    o2_column: str,
    h2_column: str,
    *,
    uptake_sign: float = -1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build sorted oxygen/hydrogen heatmap edges and growth values."""
    _require_columns(
        envelope,
        {growth_column, o2_column, h2_column},
        label="production-envelope",
    )

    data = envelope[[growth_column, o2_column, h2_column]].copy()
    data[growth_column] = _numeric_values(
        data,
        growth_column,
        label="production-envelope",
    )
    data[o2_column] = (
        uptake_sign
        * _numeric_values(
            data,
            o2_column,
            label="production-envelope",
        )
    )
    data[h2_column] = (
        uptake_sign
        * _numeric_values(
            data,
            h2_column,
            label="production-envelope",
        )
    )

    pivot = data.pivot_table(
        index=h2_column,
        columns=o2_column,
        values=growth_column,
        aggfunc="max",
        dropna=False,
        sort=True,
    )
    if pivot.empty:
        raise ValueError(
            "The production envelope contains no heatmap values."
        )

    x_centers = pivot.columns.to_numpy(dtype=float)
    y_centers = pivot.index.to_numpy(dtype=float)
    values = pivot.to_numpy(dtype=float)

    return (
        _centers_to_edges(x_centers),
        _centers_to_edges(y_centers),
        values,
    )


def plot_phpp(
    *,
    heatmap_x_edges: np.ndarray,
    heatmap_y_edges: np.ndarray,
    heatmap_values: np.ndarray,
    optimality_points: pd.DataFrame,
    optimality_fit: LinearFit,
    h2_plot_column: str,
    o2_plot_column: str,
    grouped_experimental_data: pd.DataFrame | None = None,
    experimental_h2_column: str = "H2 Flux theoretic",
    experimental_o2_column: str = "O2 flux theoretic",
    error_type: ErrorType = "std",
    experimental_fit: LinearFit | None = None,
    y_limit: float | None = None,
    figsize: tuple[float, float] = (6.3, 5.4),
    cmap: str = "viridis",
) -> tuple[Figure, Axes]:
    """Create the PhPP heatmap and regression overlays."""
    with plt.rc_context(PHPP_STYLE):
        figure, axes = plt.subplots(figsize=figsize)
        mesh = axes.pcolormesh(
            heatmap_x_edges,
            heatmap_y_edges,
            heatmap_values,
            shading="flat",
            cmap=cmap,
            edgecolors=(0, 0, 0, 0.35),
            linewidth=0.25,
            antialiased=True,
        )

        axes.set_xticks(heatmap_x_edges, minor=True)
        axes.set_yticks(heatmap_y_edges, minor=True)
        axes.grid(
            which="minor",
            color=(0, 0, 0, 0.35),
            linewidth=0.25,
        )
        axes.tick_params(which="minor", length=0)

        row_has_data = ~np.isnan(heatmap_values).all(axis=1)
        if row_has_data.any():
            first_row = int(np.argmax(row_has_data))
            lower_limit = heatmap_y_edges[first_row]
            upper_limit = (
                y_limit
                if y_limit is not None
                else heatmap_y_edges[-1]
            )
            axes.set_ylim(lower_limit, upper_limit)

        oxygen_line = np.linspace(
            optimality_points[o2_plot_column].min(),
            optimality_points[o2_plot_column].max(),
            300,
        )
        axes.plot(
            oxygen_line,
            optimality_fit.predict(oxygen_line),
            color="crimson",
            linewidth=2.0,
            zorder=5,
            label="Line of optimality",
        )

        if grouped_experimental_data is not None:
            exp_x, exp_y, exp_xerr, exp_yerr = (
                calculate_error_for_plotting(
                    grouped_experimental_data,
                    x_column=experimental_o2_column,
                    y_column=experimental_h2_column,
                    error_type=error_type,
                )
            )
            axes.errorbar(
                exp_x,
                exp_y,
                xerr=exp_xerr,
                yerr=exp_yerr,
                fmt="none",
                ecolor="black",
                elinewidth=0.9,
                capsize=2,
                alpha=0.9,
                zorder=6,
            )
            axes.scatter(
                exp_x,
                exp_y,
                color="black",
                s=34,
                zorder=7,
                label="Experimental data",
            )

            if experimental_fit is not None:
                experimental_line = np.linspace(
                    np.nanmin(exp_x),
                    np.nanmax(exp_x),
                    300,
                )
                axes.plot(
                    experimental_line,
                    experimental_fit.predict(experimental_line),
                    linestyle="--",
                    color="black",
                    linewidth=1.8,
                    zorder=6,
                    label="Experimental fit",
                )

        colorbar = figure.colorbar(
            mesh,
            ax=axes,
            pad=0.02,
            fraction=0.046,
        )
        colorbar.set_label(
            r"Growth rate ($\mathrm{h^{-1}}$)",
            labelpad=8,
        )
        colorbar.ax.tick_params(labelsize=9, width=0.6)
        colorbar.outline.set_linewidth(0.6)

        axes.set_xlabel(
            r"O$_2$ uptake rate (mmol gDW$^{-1}$ h$^{-1}$)",
            labelpad=6,
        )
        axes.set_ylabel(
            r"H$_2$ uptake rate (mmol gDW$^{-1}$ h$^{-1}$)",
            labelpad=6,
        )

        for spine in axes.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(0.5)
            spine.set_color("black")
        axes.tick_params(
            direction="out",
            length=3.5,
            width=0.5,
            top=False,
            right=False,
        )

        annotation_lines = [
            r"$\mathbf{Line\ of\ optimality}$",
            (
                rf"H$_2$ = {optimality_fit.slope:.2f}"
                rf"$\cdot$O$_2$ {optimality_fit.intercept:+.2f}"
            ),
        ]
        if experimental_fit is not None:
            annotation_lines.extend(
                [
                    "",
                    r"$\mathbf{Experimental\ fit}$",
                    (
                        rf"H$_2$ = {experimental_fit.slope:.2f}"
                        rf"$\cdot$O$_2$ "
                        rf"{experimental_fit.intercept:+.2f}"
                    ),
                    rf"$R^2$ = {experimental_fit.r_squared:.2f}",
                ]
            )

        axes.text(
            0.7,
            0.5,
            "\n".join(annotation_lines),
            transform=axes.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            linespacing=1.6,
            bbox={
                "boxstyle": "round,pad=0.4",
                "facecolor": "white",
                "edgecolor": (0, 0, 0, 0.5),
                "linewidth": 0.6,
                "alpha": 0.92,
            },
        )
        axes.legend(
            frameon=True,
            framealpha=0.9,
            edgecolor=(0, 0, 0, 0.3),
            fancybox=False,
            loc="lower right",
            handlelength=1.8,
            borderpad=0.6,
        )
        figure.tight_layout()

    return figure, axes


def analyze_phpp(
    production_envelope_data: DataSource,
    experimental_data: DataSource | None = None,
    *,
    growth_column: str = "flux_maximum",
    h2_column: str = "EX_h2_e",
    o2_column: str = "EX_o2_e",
    experimental_h2_column: str = "H2 Flux theoretic",
    experimental_o2_column: str = "O2 flux theoretic",
    replicate_count: int = 3,
    experimental_group_column: str | None = None,
    error_type: ErrorType = "std",
    uptake_sign: float = -1.0,
    output_path: PathLike | None = None,
    show: bool = False,
    y_limit: float | None = None,
    figsize: tuple[float, float] = (6.3, 5.4),
    cmap: str = "viridis",
) -> PhppResult:
    """Analyse and plot an existing phenotype phase plane.

    Data may be supplied as DataFrames or as CSV/Excel paths. Experimental
    data is optional.
    """
    if error_type not in {"std", "sem"}:
        raise ValueError("error_type must be either 'std' or 'sem'.")
    if uptake_sign == 0:
        raise ValueError("uptake_sign must be non-zero.")

    envelope = _load_dataframe(
        production_envelope_data,
        label="production-envelope",
    )
    _require_columns(
        envelope,
        {growth_column, h2_column, o2_column},
        label="production-envelope",
    )

    h2_plot_column = "_afaa_h2_uptake"
    o2_plot_column = "_afaa_o2_uptake"
    prepared_envelope = envelope.copy()
    prepared_envelope[growth_column] = _numeric_values(
        prepared_envelope,
        growth_column,
        label="production-envelope",
    )
    prepared_envelope[h2_plot_column] = (
        uptake_sign
        * _numeric_values(
            prepared_envelope,
            h2_column,
            label="production-envelope",
        )
    )
    prepared_envelope[o2_plot_column] = (
        uptake_sign
        * _numeric_values(
            prepared_envelope,
            o2_column,
            label="production-envelope",
        )
    )

    feasible = prepared_envelope.dropna(
        subset=[
            h2_plot_column,
            o2_plot_column,
            growth_column,
        ]
    ).copy()
    if feasible.empty:
        raise ValueError(
            "The production envelope contains no feasible numeric points."
        )

    optimality_points, optimality_fit = _calculate_optimality(
        feasible,
        growth_column=growth_column,
        h2_plot_column=h2_plot_column,
        o2_plot_column=o2_plot_column,
    )
    heatmap_x_edges, heatmap_y_edges, heatmap_values = (
        build_heatmap_grid(
            envelope,
            growth_column,
            o2_column,
            h2_column,
            uptake_sign=uptake_sign,
        )
    )

    grouped_experimental_data = None
    experimental_fit = None
    if experimental_data is not None:
        experimental = _load_dataframe(
            experimental_data,
            label="experimental",
        )
        _require_columns(
            experimental,
            {
                experimental_h2_column,
                experimental_o2_column,
            },
            label="experimental",
        )
        experimental[experimental_h2_column] = _numeric_values(
            experimental,
            experimental_h2_column,
            label="experimental",
        )
        experimental[experimental_o2_column] = _numeric_values(
            experimental,
            experimental_o2_column,
            label="experimental",
        )

        grouped_experimental_data = group_experimental_data(
            experimental,
            replicate_count=replicate_count,
            group_column=experimental_group_column,
        )
        experimental_fit = fit_linear_regression(
            grouped_experimental_data[experimental_o2_column],
            grouped_experimental_data[experimental_h2_column],
        )

    figure, axes = plot_phpp(
        heatmap_x_edges=heatmap_x_edges,
        heatmap_y_edges=heatmap_y_edges,
        heatmap_values=heatmap_values,
        optimality_points=optimality_points,
        optimality_fit=optimality_fit,
        h2_plot_column=h2_plot_column,
        o2_plot_column=o2_plot_column,
        grouped_experimental_data=grouped_experimental_data,
        experimental_h2_column=experimental_h2_column,
        experimental_o2_column=experimental_o2_column,
        error_type=error_type,
        experimental_fit=experimental_fit,
        y_limit=y_limit,
        figsize=figsize,
        cmap=cmap,
    )

    if output_path is not None:
        figure.savefig(Path(output_path), bbox_inches="tight")
    if show:
        plt.show()

    return PhppResult(
        envelope=envelope,
        grouped_experimental_data=grouped_experimental_data,
        optimality_points=optimality_points,
        optimality_fit=optimality_fit,
        experimental_fit=experimental_fit,
        heatmap_x_edges=heatmap_x_edges,
        heatmap_y_edges=heatmap_y_edges,
        heatmap_values=heatmap_values,
        figure=figure,
        axes=axes,
    )


def phpp(
    model: Model,
    h2_reaction_id: str = "EX_h2_e",
    o2_reaction_id: str = "EX_o2_e",
    *,
    objective=None,
    points: int = 20,
    experimental_data: DataSource | None = None,
    output_path: PathLike | None = None,
    show: bool = False,
    **analysis_options,
) -> PhppResult:
    """Compute, analyse, and plot a phenotype phase plane for a model."""
    envelope = compute_phpp(
        model,
        h2_reaction_id=h2_reaction_id,
        o2_reaction_id=o2_reaction_id,
        objective=objective,
        points=points,
    )
    return analyze_phpp(
        envelope,
        experimental_data=experimental_data,
        h2_column=h2_reaction_id,
        o2_column=o2_reaction_id,
        output_path=output_path,
        show=show,
        **analysis_options,
    )


__all__ = [
    "LinearFit",
    "PhppResult",
    "analyze_phpp",
    "build_heatmap_grid",
    "calculate_error_for_plotting",
    "calculate_optimality_line",
    "compute_phpp",
    "fit_linear_regression",
    "get_exp_linear_regression",
    "group_experimental_data",
    "phpp",
    "plot_phpp",
]
