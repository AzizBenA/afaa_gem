"""Loading and saving COBRA metabolic models."""

from pathlib import Path
from typing import TypeAlias

from cobra import Model
from cobra.io import read_sbml_model, write_sbml_model


PathLike: TypeAlias = str | Path


def load_sbml_model(path: PathLike) -> Model:
    """Load a COBRA model from an SBML file.

    Parameters
    ----------
    path:
        Path to an SBML or XML model file.

    Returns
    -------
    cobra.Model
        Loaded metabolic model.

    Raises
    ------
    FileNotFoundError
        If the specified model file does not exist.
    """
    model_path = Path(path)

    if not model_path.is_file():
        raise FileNotFoundError(
            f"Model file does not exist: {model_path}"
        )

    return read_sbml_model(str(model_path))


def save_sbml_model(model: Model, path: PathLike) -> Path:
    """Save a COBRA model as an SBML file."""
    output_path = Path(path)
    write_sbml_model(model, str(output_path))
    return output_path