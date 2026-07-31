"""AFAA: Analysis Framework for Flux and Annotation."""

from afaa.energy_maintenance import (
    EnergyMaintenanceResult,
    MaintenanceCandidate,
    optimize_energy_maintenance,
)
from afaa.model_io import load_sbml_model, save_sbml_model
from afaa.phpp import PhppResult, analyze_phpp, phpp
from afaa.workbench import Workbench

__all__ = [
    "EnergyMaintenanceResult",
    "MaintenanceCandidate",
    "PhppResult",
    "Workbench",
    "analyze_phpp",
    "load_sbml_model",
    "optimize_energy_maintenance",
    "phpp",
    "save_sbml_model",
]

__version__ = "0.3.0"
