# AFAA-GEM

AFAA-GEM is a Python toolkit for constructing, inspecting, curating, validating,
and analysing genome-scale metabolic models with
[COBRApy](https://opencobra.github.io/cobrapy/).

The project collects recurring model-development operations in a reusable Python
package. It includes utilities for SBML input and output, reaction and metabolite
inspection, flux analysis, biomass-reaction maintenance, model comparison,
BiGG database queries, charge curation, and Excel export.

The package is installed from PyPI as `afaa-gem` and imported in Python as
`afaa`.

> **Project status:** AFAA GEM is currently an early-stage package. Review model
> changes and optimisation results before using them in a production curation
> workflow.
## TODO:

-Add the analysis part

## Features

- Load and save COBRA models in SBML/XML format.
- Search reactions and inspect reactions, metabolites, and gene associations.
- Optimise models and extract active reaction fluxes.
- Compute and visualise phenotype phase planes with optional experimental data.
- Calibrate GAM and NGAM values against experimental growth measurements.
- Update biomass coefficients and growth-associated maintenance requirements.
- Compare biomass composition between a model and a tabular data source.
- Compare curated and non-curated models.
- Add missing reactions and metabolites without changing the input model.
- Query reactions and metabolites through the BiGG Models API.
- Identify mass- or charge-imbalanced reactions.
- Update metabolite charges from Excel or BiGG data.
- Export reaction, metabolite, and flux-summary tables to Excel.
- Use a small `Workbench` facade for common operations on one model.

## Repository layout

```text
afaa_gem/
├── pyproject.toml
├── README.md
├── src/
│   └── afaa/
│       ├── __init__.py
│       ├── bigg.py
│       ├── biomass.py
│       ├── curation.py
│       ├── energy_maintenance.py
│       ├── export.py
│       ├── flux.py
│       ├── inspection.py
│       ├── model_io.py
│       ├── phpp.py
│       ├── validation.py
│       └── workbench.py
└── tests/
    ├── conftest.py
    ├── test_bigg.py
    ├── test_curation.py
    ├── test_energy_maintenance.py
    ├── test_model_io.py
    └── test_phpp.py
```

The project uses the recommended `src` layout. Package source code lives under
`src/afaa`, while tests are kept outside the installed package under `tests`.

## Requirements

- Python 3.10 or newer
- [COBRApy](https://opencobra.github.io/cobrapy/)
- pandas
- requests
- openpyxl
- NumPy
- Matplotlib

The complete runtime dependency list is maintained in `pyproject.toml`.

## Installation

### Install from PyPI

Create and activate a virtual environment first.

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install afaa-gem
```

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install afaa-gem
```

Verify the installation:

```bash
python -c "import afaa; print(afaa.__version__)"
```

### Install with Conda

AFAA GEM is installed with `pip` inside a Conda environment:

```powershell
conda create --name afaa-gem python=3.12
conda activate afaa-gem
python -m pip install afaa-gem
```

When a Conda environment is active on Windows, use `python -m ...` rather than
`py -m ...`; the Windows `py` launcher may select a different interpreter.

### Install from the source repository

```bash
git clone https://github.com/AzizBenA/afaa_gem.git
cd afaa_gem
python -m pip install -e .
```

The editable installation makes changes under `src/afaa` immediately available
without rebuilding the package.

### Install development dependencies

```bash
python -m pip install -e ".[dev]"
```

The development extra installs pytest, coverage support, the package builder,
and Twine.

## Quick start

### Load, optimise, inspect, and save a model

```python
from afaa import Workbench, load_sbml_model, save_sbml_model

model = load_sbml_model("model.xml")
solution = model.optimize()

print(solution.status)
print(solution.objective_value)

workbench = Workbench(model)
active = workbench.get_active_reactions(solution, threshold=1e-6)
print(active.head())

workbench.reaction_details("Growth")
save_sbml_model(model, "model_updated.xml")
```

### Search for reactions

```python
from afaa.inspection import find_reactions
from afaa.model_io import load_sbml_model

model = load_sbml_model("model.xml")
matches = find_reactions(model, "biomass")
print(matches)
```

### Query BiGG

```python
from afaa.bigg import BiggClient

client = BiggClient(timeout=30)
reaction_data = client.get_reaction("PGI")

print(reaction_data["bigg_id"])
```

BiGG requests require network access. HTTP errors are raised by `requests`
rather than being converted into empty results.

### Run a phenotype phase plane analysis

Calculate a production envelope directly from a COBRA model, fit its line of
optimality, optionally compare it with experimental H2/O2 uptake measurements,
and create a heatmap:

```python
from afaa import load_sbml_model, phpp

model = load_sbml_model("model.xml")

result = phpp(
    model,
    h2_reaction_id="EX_h2_e",
    o2_reaction_id="EX_o2_e",
    experimental_data="experimental_gases.xlsx",
    experimental_h2_column="measured_hydrogen_uptake",
    experimental_o2_column="measured_oxygen_uptake",
    points=20,
    error_type="sem",
    output_path="phpp_analysis.png",
    show=False,
)

print(result.optimality_fit.slope)
print(result.optimality_fit.intercept)

if result.experimental_fit is not None:
    print(result.experimental_fit.r_squared)
```

The returned `PhppResult` retains the source envelope, grouped experimental
data, fitted lines, heatmap arrays, Matplotlib figure, and axes. Omitting
`experimental_data` performs a model-only analysis.

The same workflow is available from a workbench:

```python
workbench = Workbench(model)
result = workbench.phpp(
    h2_reaction_id="EX_h2_e",
    o2_reaction_id="EX_o2_e",
    points=20,
)
```

### Optimise GAM and NGAM

Search explicit GAM and NGAM candidate values against experimental growth data:

```python
import numpy as np
import pandas as pd

from afaa import load_sbml_model, optimize_energy_maintenance

model = load_sbml_model("model.xml")
experimental = pd.read_excel("growth_measurements.xlsx")

result = optimize_energy_maintenance(
    model,
    experimental,
    gam_values=np.arange(10, 151, 10),
    ngam_values=np.arange(0, 16, 1),
    biomass_reaction_id="Growth",
    atpm_reaction_id="ATPM",
    experimental_growth_column="measured_growth",
    experimental_h2_column="measured_hydrogen_uptake",
    output_path="energy_maintenance_results.xlsx",
)

print(result.best_by_mean_difference)
print(result.best_by_r2)
print(result.combinations.head())
```

NGAM candidates can instead be estimated by maximizing ATP-maintenance flux at
fixed hydrogen uptake values:

```python
result = optimize_energy_maintenance(
    model,
    experimental,
    gam_values=np.arange(10, 151, 10),
    h2_uptake_values=np.arange(8.7, 14.8, 0.1),
    experimental_growth_column="measured_growth",
    experimental_h2_column="measured_hydrogen_uptake",
)
```

Provide exactly one of `ngam_values` or `h2_uptake_values`. The search uses
COBRA model contexts, so objectives, bounds, and GAM coefficients are restored
after every candidate is evaluated.

### Update GAM coefficients

```python
from afaa.biomass import update_gam

growth_rate = update_gam(
    model,
    reaction_id="Growth",
    gam_dict_1={"atp_c": -49.0, "h2o_c": -49.0},
    gam_dict_2={"adp_c": 49.0, "pi_c": 49.0, "h_c": 49.0},
)

print(growth_rate)
```

## Model mutation and return-value conventions

The functions do not all handle models in the same way:

| Operation | Behaviour |
|---|---|
| `update_biomass_from_dataframe` | Mutates the supplied model |
| `update_gam` | Mutates the supplied model |
| `update_metabolite_charges_from_excel` | Mutates the supplied model |
| `update_metabolite_charges_from_bigg` | Mutates the supplied model |
| `reaction_flux` | Changes the supplied model's objective |
| `compute_phpp` and `phpp` | Analyse the model without intentionally changing it |
| `optimize_energy_maintenance` | Searches temporary model contexts and restores the input model |
| `update_metabolite_info` | Returns an updated copy |
| `add_missing_reactions` | Returns an updated copy |
| `add_missing_metabolites` | Returns an updated copy |
| Inspection, validation, and export functions | Do not intentionally alter model structure |

Assign the result when a function returns a model copy:

```python
updated_model = add_missing_reactions(non_curated_model, curated_model)
```

For an in-place function, keep a copy when rollback may be necessary:

```python
backup = model.copy()
update_gam(model)
```

## Public API reference

`Workbench`, PHPP APIs, energy-maintenance APIs, `load_sbml_model`, and
`save_sbml_model` are re-exported from the top-level `afaa` namespace. Import
the remaining functions from their individual modules.

### `afaa.model_io`

#### `load_sbml_model(path) -> cobra.Model`

Load a COBRA model from an SBML or XML file.

- `path`: A string or `pathlib.Path` pointing to the input model.
- Returns: The model returned by `cobra.io.read_sbml_model`.
- Raises: `FileNotFoundError` when the path does not identify an existing file.

```python
from afaa import load_sbml_model

model = load_sbml_model("models/input.xml")
```

#### `save_sbml_model(model, path) -> pathlib.Path`

Write a COBRA model to an SBML/XML file.

- `model`: The `cobra.Model` to serialize.
- `path`: Destination represented by a string or `pathlib.Path`.
- Returns: The destination as a `pathlib.Path`.
- Side effect: Creates or overwrites the destination file.

```python
from afaa import save_sbml_model

output_path = save_sbml_model(model, "models/output.xml")
```

### `afaa.bigg`

#### `BiggClient(base_url="http://bigg.ucsd.edu/api/v2", timeout=15, session=None)`

Client for the BiGG Models HTTP API.

- `base_url`: API root. A trailing slash is removed automatically.
- `timeout`: Request timeout in seconds.
- `session`: Optional `requests.Session`. Supplying a session supports
  connection reuse and makes the client straightforward to mock in tests.
- Attributes: `base_url`, `timeout`, and `session`.

```python
import requests

from afaa.bigg import BiggClient

session = requests.Session()
client = BiggClient(timeout=20, session=session)
```

#### `BiggClient.get_reaction(reaction_id) -> dict`

Retrieve a universal BiGG reaction.

- `reaction_id`: Universal BiGG reaction identifier.
- Endpoint: `/universal/reactions/{reaction_id}`.
- Returns: The decoded JSON response as a dictionary.
- Raises: A `requests` exception for connection, timeout, or HTTP errors.

#### `BiggClient.get_metabolite(model_id, metabolite_id) -> dict`

Retrieve a metabolite from a specific BiGG model.

- `model_id`: BiGG model identifier, for example `iJO1366`.
- `metabolite_id`: Model-specific metabolite identifier, for example `atp_c`.
- Endpoint: `/models/{model_id}/metabolites/{metabolite_id}`.
- Returns: The decoded JSON response as a dictionary.
- Raises: A `requests` exception for connection, timeout, or HTTP errors.

### `afaa.inspection`

#### `find_reactions(model, search_term) -> pandas.DataFrame`

Search reaction IDs using a case-insensitive substring.

- `model`: A `cobra.Model`.
- `search_term`: Text to find in each reaction ID.
- Returns: A DataFrame containing `id`, `name`, `equation`, bounds, genes, and
  annotation for every match.
- An empty search result produces an empty DataFrame.

```python
from afaa.inspection import find_reactions

transport_reactions = find_reactions(model, "tex")
```

#### `find_metabolites(model, search_word) -> None`

Print details for metabolites whose IDs contain a case-sensitive substring.
The output includes name, formula, charge, compartment, annotations, related
reactions, and associated genes.

- `model`: A `cobra.Model`.
- `search_word`: Substring to search for in metabolite IDs.
- Returns: `None`; results are written to standard output.

#### `reaction_details(model, reaction_id) -> None`

Print a reaction's identifier, name, equation, bounds, metabolite
stoichiometry, calculated net charge, and associated genes.

- `model`: A `cobra.Model`.
- `reaction_id`: Exact reaction identifier.
- Returns: `None`.
- Missing reactions are reported to standard output.

#### `gene_reaction_details(model, gene_id) -> None`

Print a gene and all associated reactions, including reaction equations,
bounds, and metabolite coefficients.

- `model`: A `cobra.Model`.
- `gene_id`: Exact gene identifier.
- Returns: `None`.
- Missing genes are reported to standard output.

### `afaa.flux`

#### `reaction_flux(objective_rxn, model, reaction_id) -> float | None`

Set a model objective, optimise the model, and report the flux through one
reaction.

- `objective_rxn`: Objective accepted by COBRApy's `model.objective`.
- `model`: A `cobra.Model`.
- `reaction_id`: Reaction whose flux should be returned.
- Returns: The reaction flux when optimisation is optimal and the reaction is
  present; otherwise `None`.
- Side effect: Replaces the model's current objective.
- Output: Prints optimisation or flux information.

#### `get_active_reactions_for_metabolite(model, solution, metabolite_id, flux_threshold=0.5) -> list`

Find reactions involving a particular metabolite whose absolute flux exceeds a
threshold.

- `model`: A `cobra.Model`.
- `solution`: A COBRApy solution containing fluxes for the model.
- `metabolite_id`: Exact metabolite identifier.
- `flux_threshold`: Strict lower bound on absolute flux.
- Returns: A list of `[reaction name, reaction ID, equation, flux]` rows.
- Returns an empty list when the metabolite is missing.

#### `get_active_reactions(model, solution, threshold=1e-9) -> pandas.DataFrame`

Collect all reactions whose absolute flux exceeds `threshold`.

- `model`: A `cobra.Model`.
- `solution`: A compatible COBRApy optimisation solution.
- `threshold`: Strict lower bound on absolute flux.
- Returns: A DataFrame with `Reaction Name`, `Reaction ID`, and `Flux Value`.

```python
from afaa.flux import get_active_reactions

solution = model.optimize()
active = get_active_reactions(model, solution, threshold=1e-6)
```

### `afaa.biomass`

#### `update_biomass_from_dataframe(model, biomass_df, reaction_id="Growth", id_column="Biomass_equation", coeff_column="normalized_mmol/g") -> int`

Replace coefficients in a biomass reaction using values from a pandas
DataFrame.

- `model`: Model to update.
- `biomass_df`: DataFrame containing metabolite IDs and coefficients.
- `reaction_id`: Biomass reaction to edit.
- `id_column`: Column containing metabolite identifiers.
- `coeff_column`: Column containing replacement coefficients.
- Returns: Number of matched metabolites that were updated.
- Side effects: Mutates the reaction, runs `model.slim_optimize()` after every
  update, and prints progress.
- Metabolites listed in the DataFrame but absent from the reaction are skipped.

#### `find_missing_biomass_metabolites(model, biomass_df, reaction_id="Growth", source="Dataframe", id_column="Biomass_equation", coeff_column="normalized_mmol/g", name_column="Unnamed: 1", output_path=None) -> pandas.DataFrame`

Compare the metabolites in a biomass reaction with the metabolites listed in a
DataFrame.

- `source="Dataframe"`: Return DataFrame metabolites missing from the model
  biomass reaction.
- `source="Model"`: Return model biomass metabolites missing from the
  DataFrame.
- `output_path`: When supplied, also write the result to Excel.
- Returns: A DataFrame with `metabolite_id`, `metabolite_name`, and
  `coefficient`.
- Raises: `ValueError` for an unsupported `source`, `KeyError` for missing
  required columns, or `KeyError` when the biomass reaction does not exist.

The `source` value is case-sensitive.

#### `compare_biomass_metabolites_between_models(model_a, model_b, reaction_id_a="Growth", reaction_id_b="BIOMASS_KT2440_WT3") -> pandas.DataFrame`

Compare two biomass reactions and list metabolites found in `model_b` but
absent from `model_a`.

- `model_a`: Reference model.
- `model_b`: Comparison model.
- `reaction_id_a`: Biomass reaction in the reference model.
- `reaction_id_b`: Biomass reaction in the comparison model.
- Returns: A DataFrame containing `metabolite_id` and `metabolite_name`.
- Missing reaction IDs propagate as `KeyError`.

#### `update_gam(model, reaction_id="Growth", gam_dict_1=None, gam_dict_2=None, verbose=True) -> float`

Update growth-associated maintenance (GAM) coefficients in a biomass reaction
and re-optimise the model.

Default reactant-side coefficients:

```python
{"atp_c": -49.0, "h2o_c": -49.0}
```

Default product-side coefficients:

```python
{"adp_c": 49.0, "pi_c": 49.0, "h_c": 49.0}
```

- `model`: Model to mutate.
- `reaction_id`: Biomass reaction identifier.
- `gam_dict_1` and `gam_dict_2`: Replacement coefficients keyed by metabolite
  ID.
- `verbose`: Print changed coefficients and the resulting growth rate.
- Returns: Result of `model.slim_optimize()`.
- Metabolites that exist in the model but not in the biomass reaction are
  skipped.

### `afaa.curation`

#### `update_metabolite_charges_from_excel(model, excel_path, id_column="metabolite changed", charge_column="New charge") -> int`

Read metabolite charges from an Excel file and apply them to a model.

- `model`: Model to mutate.
- `excel_path`: Path accepted by `pandas.read_excel`.
- `id_column`: Excel column containing metabolite IDs.
- `charge_column`: Excel column containing new charge values.
- Returns: Number of updated rows.
- Charge values are converted to integers.
- Unknown metabolite IDs are skipped and reported.

#### `find_bigg_reference_models(model, client, limit=None, verbose=True) -> dict`

Find BiGG reference models for mass- or charge-imbalanced reactions.

- `model`: Model checked with COBRApy's mass-balance validator.
- `client`: A configured `BiggClient`.
- `limit`: Optional maximum number of imbalanced reactions to query. `None`
  means no limit.
- `verbose`: Print individual reaction mappings.
- Returns: A dictionary mapping local reaction IDs to the first BiGG model
  reported in `models_containing_reaction`.
- Network and API errors propagate from `BiggClient`.

```python
from afaa.bigg import BiggClient
from afaa.curation import find_bigg_reference_models

client = BiggClient()
mapping = find_bigg_reference_models(
    model,
    client,
    limit=20,
    verbose=True,
)
```

#### `update_metabolite_charges_from_bigg(model, client, reaction_model_mapping) -> int`

Use BiGG metabolite data to update zero-charge metabolites found in mapped
reactions.

- `model`: Model to mutate.
- `client`: A configured `BiggClient`.
- `reaction_model_mapping`: Mapping from local reaction IDs to BiGG model IDs,
  typically returned by `find_bigg_reference_models`.
- Returns: Number of metabolite charge updates.
- Missing local reactions are skipped.
- Network and API errors propagate from `BiggClient`.

#### `update_metabolite_info(non_curated_model, curated_model) -> cobra.Model`

Copy charge and formula values from a curated model to matching metabolites in
a non-curated model.

- Matching is performed by exact metabolite ID.
- Returns: An updated copy of `non_curated_model`.
- Input models are not intentionally changed.
- Metabolites missing from the curated model are reported and left unchanged.

#### `add_missing_reactions(non_curated_model, curated_model) -> cobra.Model`

Add reactions that occur in a curated model but not in a non-curated model.

- Matching is performed by exact reaction ID.
- Reactions are copied before being added.
- Returns: An updated copy of `non_curated_model`.
- The returned model is optimised and its objective value is printed.

#### `add_missing_metabolites(non_curated_model, curated_model) -> cobra.Model`

Add metabolites that occur in a curated model but not in a non-curated model.

- Matching is performed by exact metabolite ID.
- Copies ID, name, formula, compartment, charge, and annotation.
- Returns: An updated copy of `non_curated_model`.
- This function adds metabolite objects only; it does not add reactions that use
  them.

### `afaa.validation`

#### `check_model_mass_balance(model) -> None`

Run COBRApy's mass-balance validation and print the number of imbalanced
reactions followed by each reaction ID and imbalance dictionary.

- `model`: Model to validate.
- Returns: `None`.
- Output is written to standard output rather than returned as structured data.

### `afaa.export`

All export functions write `.xlsx` files through pandas and openpyxl.

#### `build_metabolite_summary(model, summary, file_path) -> None`

Combine the producing and consuming flux tables from a COBRApy metabolite
summary, order them by absolute flux, enrich them with reaction names,
equations, and genes, and write the result to Excel.

- `model`: Model used to resolve reaction metadata.
- `summary`: COBRApy metabolite summary with `producing_flux` and
  `consuming_flux` DataFrames.
- `file_path`: Excel destination.
- Side effect: Adds a `type` column to the producing and consuming tables.
- Returns: The return value of `DataFrame.to_excel`, normally `None`.

#### `export_reactions_to_excel(model, file_path) -> None`

Write all reactions to Excel.

The output includes reaction ID, name, equation, lower and upper bounds,
gene-reaction rule, and annotations.

#### `export_metabolites_to_excel(model, file_path) -> None`

Write all metabolites to Excel.

The output includes metabolite ID, name, formula, charge, and related reaction
objects.

#### `export_metabolites_from_reaction(model, reaction_id, file_path) -> None`

Write the metabolites and stoichiometric coefficients of one reaction to
Excel.

- `reaction_id`: Exact reaction identifier.
- The output contains metabolite ID, name, coefficient, and charge.
- Reaction details are also printed.
- A missing reaction is reported without creating a result table.

### `afaa.energy_maintenance`

The energy-maintenance module calibrates growth-associated maintenance (GAM)
and non-growth-associated maintenance (NGAM) against measured growth rates.
GAM is represented by ATP hydrolysis coefficients in the biomass reaction;
NGAM is represented by the lower bound of the ATP-maintenance reaction.

The calibration workflow is import-safe and contains no interactive prompts,
hard-coded file paths, or automatic exports. Model changes are made inside
COBRA contexts and are reverted after evaluation.

#### `optimize_energy_maintenance(model, experimental_data, gam_values, *, experimental_growth_column, experimental_h2_column, ngam_values=None, h2_uptake_values=None, ...) -> EnergyMaintenanceResult`

Evaluate the Cartesian product of GAM and NGAM candidates. Exactly one NGAM
source is required:

- `ngam_values`: Explicit ATP-maintenance lower bounds.
- `h2_uptake_values`: Hydrogen uptake values used to estimate maximum feasible
  ATP-maintenance fluxes with `estimate_ngam`.

Map the experimental DataFrame explicitly with these required keyword
arguments:

| Argument | Meaning |
|---|---|
| `experimental_growth_column` | Name of the measured growth or dilution-rate column |
| `experimental_h2_column` | Name of the non-negative measured H2 uptake column |

Default model reaction IDs are:

| Parameter | Default |
|---|---|
| Biomass objective | `Growth` |
| ATP maintenance | `ATPM` |
| Hydrogen exchange | `EX_h2_e` |
| Oxygen exchange | `EX_o2_e` |
| Carbon-dioxide exchange | `EX_co2_e` |

Model identifiers have documented defaults. Experimental column names have no
defaults, so the caller must map them explicitly. `output_path` optionally
writes the complete candidate table to CSV or Excel.

#### `EnergyMaintenanceResult`

Contains:

- `combinations`: DataFrame with `H2_uptake_basis`, `NGAM_value`, `GAM_value`,
  `Mean_Difference`, and `R2_Score`.
- `best_by_mean_difference`: Candidate with the lowest mean absolute error.
- `best_by_r2`: Candidate with the highest coefficient of determination.

The two best candidates may differ, so the result reports both rather than
silently choosing one scoring criterion.

#### `MaintenanceCandidate`

Immutable description of one candidate with `gam`, `ngam`,
`mean_difference`, `r2_score`, and optional `h2_uptake_basis` attributes.

#### `compute_growth_rates(model, experimental_data, *, experimental_h2_column, **options) -> pandas.DataFrame`

Apply each experimental H2 uptake constraint, optimise growth, and return a
copy of the input DataFrame with these additional columns:

- `growth_rate`
- `H2 Flux model`
- `O2 Flux model`
- `CO2 Flux model`

Infeasible conditions remain `NaN`. The model objective and bounds are restored
after the function returns.

#### `set_gam(model, gam_value, **options) -> None`

Set absolute ATP, water, ADP, phosphate, and proton coefficients in the biomass
reaction. Unlike the search workflow, this low-level function intentionally
modifies the supplied model. It raises an error if a required metabolite is
missing from the biomass reaction.

#### Other maintenance helpers

- `estimate_ngam`: Maximise ATP-maintenance flux at a fixed H2 uptake.
- `calculate_difference_for_gam`: Temporarily apply one GAM value, simulate all
  experimental conditions, and return mean absolute error and R-squared.
- `compute_mean_difference`: Calculate mean absolute experimental/simulated
  growth error after excluding missing pairs.
- `compute_r2_score`: Calculate the coefficient of determination after
  excluding missing pairs.

### `afaa.phpp`

The PHPP module calculates and visualises two-dimensional phenotype phase
planes. Its high-level model workflow uses COBRApy's `production_envelope`.
Existing production-envelope CSV, Excel, or DataFrame data can also be analysed
without recomputing the model.

Importing `afaa.phpp` does not read files, modify Matplotlib's global style, or
display a figure.

#### `phpp(model, h2_reaction_id="EX_h2_e", o2_reaction_id="EX_o2_e", *, experimental_h2_column=None, experimental_o2_column=None, objective=None, points=20, experimental_data=None, output_path=None, show=False, **analysis_options) -> PhppResult`

Run the complete model-based workflow:

1. Calculate a production envelope.
2. Convert uptake fluxes to positive plotting values.
3. Find maximum-growth points for each hydrogen uptake.
4. Resolve growth ties using the lowest oxygen uptake.
5. Fit the model line of optimality.
6. Optionally group and fit experimental measurements.
7. Build and optionally save the PHPP figure.

The function uses the model's current objective unless `objective` is supplied.
`points` specifies the number of envelope grid points per reaction and must be
at least two.

Common analysis options forwarded to `analyze_phpp` include:

- `growth_column`, default `flux_maximum`
- `experimental_h2_column`, the experimental H2 uptake column; required when
  `experimental_data` is provided
- `experimental_o2_column`, the experimental O2 uptake column; required when
  `experimental_data` is provided
- `replicate_count`, default `3`
- `experimental_group_column`, default `None`
- `error_type`, either `std` or `sem`
- `uptake_sign`, default `-1.0`
- `y_limit`, `figsize`, and `cmap`

#### `compute_phpp(model, h2_reaction_id="EX_h2_e", o2_reaction_id="EX_o2_e", *, objective=None, points=20) -> pandas.DataFrame`

Calculate only the COBRApy production envelope. This is useful when computation
and plotting happen in separate workflows.

```python
from afaa.phpp import compute_phpp

envelope = compute_phpp(
    model,
    h2_reaction_id="EX_h2_e",
    o2_reaction_id="EX_o2_e",
    points=30,
)
envelope.to_csv("production_envelope.csv", index=False)
```

Missing reaction IDs raise `KeyError`. A `points` value below two raises
`ValueError`.

#### `analyze_phpp(production_envelope_data, experimental_data=None, **options) -> PhppResult`

Analyse a previously calculated envelope supplied as:

- a pandas DataFrame;
- a `.csv` path; or
- an `.xlsx`/`.xls` path.

Experimental data accepts the same input forms. It is optional, so the
model-optimality heatmap can be produced by itself:

```python
from afaa import analyze_phpp

result = analyze_phpp(
    "production_envelope.csv",
    growth_column="flux_maximum",
    h2_column="EX_h2_e",
    o2_column="EX_o2_e",
    output_path="production_envelope.pdf",
)
```

`show` defaults to `False`, which is suitable for tests, notebooks, pipelines,
and headless systems. Set `show=True` for an interactive Matplotlib window.

#### `PhppResult`

Structured analysis result with these attributes:

| Attribute | Description |
|---|---|
| `envelope` | Original production-envelope DataFrame |
| `grouped_experimental_data` | Replicate means and error statistics, or `None` |
| `optimality_points` | Maximum-growth points used for the model fit |
| `optimality_fit` | Model `LinearFit` |
| `experimental_fit` | Experimental `LinearFit`, or `None` |
| `heatmap_x_edges` | Oxygen uptake bin edges |
| `heatmap_y_edges` | Hydrogen uptake bin edges |
| `heatmap_values` | Growth-rate heatmap matrix |
| `figure` | Matplotlib `Figure` |
| `axes` | Main Matplotlib `Axes` |

The figure remains open after the call so callers can customise or save it:

```python
result.axes.set_title("Hydrogen-oxygen phenotype phase plane")
result.figure.savefig("custom_phpp.svg", bbox_inches="tight")
```

#### `LinearFit`

Immutable line-fit result containing `slope`, `intercept`, and `r_squared`.
Use `fit.predict(values)` to evaluate the line.

#### PHPP helper functions

- `group_experimental_data`: Group by a condition column or by consecutive
  replicate blocks, returning means, standard deviations, standard errors, and
  counts.
- `fit_linear_regression`: Fit a line with NumPy and return `LinearFit`.
- `calculate_error_for_plotting`: Extract experimental values and either SD or
  SEM arrays.
- `calculate_optimality_line`: Extract the optimal model points and fitted line.
- `build_heatmap_grid`: Create sorted heatmap edges and growth values.
- `plot_phpp`: Build the Matplotlib figure from prepared numerical results.

### `afaa.workbench`

#### `Workbench(model)`

Store a COBRA model and expose selected package operations as methods.

```python
from afaa import Workbench

workbench = Workbench(model)
```

#### `Workbench.reaction_details(reaction_id)`

Delegate to `afaa.inspection.reaction_details` using the stored model.

#### `Workbench.get_active_reactions(solution, threshold=1e-9)`

Delegate to `afaa.flux.get_active_reactions` using the stored model. Returns a
DataFrame of reactions exceeding the absolute flux threshold.

#### `Workbench.update_gam(reaction_id="Growth", **kwargs)`

Delegate to `afaa.biomass.update_gam` using the stored model. Extra keyword
arguments are forwarded to `update_gam`.

#### `Workbench.phpp(h2_reaction_id="EX_h2_e", o2_reaction_id="EX_o2_e", **kwargs)`

Run `afaa.phpp.phpp` with the model stored in the workbench. Keyword arguments
control production-envelope computation, experimental-data processing, plotting,
and output.

#### `Workbench.optimize_energy_maintenance(experimental_data, gam_values, **kwargs)`

Run `afaa.energy_maintenance.optimize_energy_maintenance` using the model stored
in the workbench.

## Working with Excel

Excel input and output uses pandas with openpyxl. Paths can generally be strings
or path-like objects accepted by pandas.

Example charge table:

| metabolite changed | New charge |
|---|---:|
| atp_c | -4 |
| adp_c | -3 |

```python
from afaa.curation import update_metabolite_charges_from_excel

count = update_metabolite_charges_from_excel(
    model,
    "charges.xlsx",
)
print(f"Updated {count} metabolites")
```

Example reaction export:

```python
from afaa.export import export_reactions_to_excel

export_reactions_to_excel(model, "reactions.xlsx")
```

## Error handling

- Missing SBML files raise `FileNotFoundError`.
- Exact COBRA object lookups may raise `KeyError` unless the function explicitly
  handles missing IDs.
- BiGG network failures, timeouts, and non-success HTTP responses raise
  `requests` exceptions.
- Excel operations may raise pandas or openpyxl exceptions for missing files,
  missing columns, invalid values, or unwritable destinations.
- Optimisation results should be checked before interpreting fluxes or objective
  values.

For automated workflows, catch errors at the boundary:

```python
import requests

from afaa.bigg import BiggClient

client = BiggClient()

try:
    data = client.get_reaction("PGI")
except requests.RequestException as exc:
    print(f"BiGG request failed: {exc}")
```

## Testing

Install the development dependencies and run the test suite:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Run with coverage:

```bash
python -m pytest --cov=afaa --cov-report=term-missing
```

The tests use small in-memory COBRA models and mocked HTTP sessions. Unit tests
should not depend on the availability or contents of the live BiGG service.


## Development notes

- Several functions print human-readable progress instead of returning
  structured diagnostics.
- Model identifiers must follow the identifiers used by the loaded COBRA model.
- BiGG mappings use the first reference model returned by the API; selecting the
  biologically best reference remains the caller's responsibility.
- Curation operations should be validated with mass balance, charge balance,
  objective value, and domain-specific review.
- Keep package and source versions synchronized when preparing a release.

## Contributing

1. Create a feature branch.
2. Install the project with `python -m pip install -e ".[dev]"`.
3. Add or update tests for behavioural changes.
4. Run pytest and review coverage.
5. Submit a pull request describing the model or API impact.

Repository: <https://github.com/AzizBenA/afaa_gem>

## License

Copyright institute of Applied Microbiology, RWTH Aachen University, Aachen, Germany (2026)

PAModelpy is released under both the GPL and LGPL licenses version 2 or later. You may choose which license you choose to use the software under.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License or the GNU Lesser General Public License as published by the Free Software Foundation, either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
