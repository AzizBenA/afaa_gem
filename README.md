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

## Features

- Load and save COBRA models in SBML/XML format.
- Search reactions and inspect reactions, metabolites, and gene associations.
- Optimise models and extract active reaction fluxes.
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
│       ├── export.py
│       ├── flux.py
│       ├── inspection.py
│       ├── model_io.py
│       ├── validation.py
│       └── workbench.py
└── tests/
    ├── conftest.py
    ├── test_bigg.py
    ├── test_curation.py
    └── test_model_io.py
```

The project uses the recommended `src` layout. Package source code lives under
`src/afaa`, while tests are kept outside the installed package under `tests`.

## Requirements

- Python 3.10 or newer
- [COBRApy](https://opencobra.github.io/cobrapy/)
- pandas
- requests
- openpyxl

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

Only `Workbench`, `load_sbml_model`, and `save_sbml_model` are re-exported from
the top-level `afaa` namespace. Import the remaining functions from their
individual modules.

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

## Building the distribution

Build a wheel and source distribution:

```bash
python -m build
```

Validate the generated artifacts:

```bash
python -m twine check dist/*
```

Artifacts are written to `dist/`. Test the wheel in a clean virtual environment
before publishing it.

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
