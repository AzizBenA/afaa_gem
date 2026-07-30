from afaa.bigg import BiggClient
import pandas as pd
import cobra
from cobra import Metabolite



def update_metabolite_charges_from_excel(model, excel_path, id_column='metabolite changed', charge_column='New charge'):
    """
    Updates metabolite charges in a COBRA model based on values from an Excel file.

    Parameters:
    - model: COBRApy model object
    - excel_path: str or Path, path to the Excel file
    - id_column: str, column name for metabolite IDs in the Excel file
    - charge_column: str, column name for new charge values in the Excel file

    Returns:
    - int: number of successfully updated metabolites
    """
    df = pd.read_excel(excel_path)
    updated_count = 0

    for met_id in df[id_column]:
        if met_id in model.metabolites:
            metabolite = model.metabolites.get_by_id(met_id)
            new_charge = int(df.loc[df[id_column] == met_id, charge_column].values[0])
            old_charge = metabolite.charge
            metabolite.charge = new_charge
            print(f"Modified metabolite: {met_id} | Old charge: {old_charge} → New charge: {new_charge}")
            updated_count += 1
        else:
            print(f"Metabolite '{met_id}' not found in the model.")

    print(f"\n Total metabolites updated: {updated_count}")
    return updated_count


def find_bigg_reference_models(model,client: BiggClient, limit=None, verbose=True):
    """
    Retrieves BiGG model IDs for reactions that are mass/charge imbalanced in the given model.

    Parameters:
    - model: COBRApy model object
    - client: BiggClient instance for BiGG API access
    - limit: optional int, max number of reactions to check (for testing or speed)
    - verbose: bool, whether to print progress

    Returns:
    - dict: mapping of reaction ID → model ID from BiGG database
    """
    imbalanced = cobra.manipulation.validate.check_mass_balance(model)
    reaction_model_mapping = {}

    for i, reaction in enumerate(imbalanced):
        if limit is not None and i >= limit:
            break
        reaction_id = reaction.id
        data = client.get_reaction(reaction_id)
        models = data.get('models_containing_reaction', [])
        if models:
            reaction_model_mapping[reaction_id] = models[0]['bigg_id']
            if verbose:
                print(f"{reaction_id} → {models[0]['bigg_id']}")
        else:
            if verbose:
                print(f"{reaction_id} found, but no models listed.")

    print(f"\n Retrieved model info for {len(reaction_model_mapping)} imbalanced reactions.")
    return reaction_model_mapping

def update_metabolite_charges_from_bigg(model, client: BiggClient, reaction_model_mapping):
    """
    Updates zero-charge metabolites in reactions using charge values from the BiGG database.

    Parameters:
    - model: COBRApy model object
    - reaction_model_mapping: dict mapping reaction IDs to BiGG model names
    -client: BiggClient instance for BiGG API access

    Returns:
    - int: number of metabolites whose charges were updated
    """
    updated_count = 0


    for reaction_id, bigg_model_name in reaction_model_mapping.items():
        try:
            reaction = model.reactions.get_by_id(reaction_id)
        except KeyError:
            print(f"Reaction '{reaction_id}' not found in model.")
            continue

        for metabolite, coefficient in reaction.metabolites.items():
            if metabolite.charge == 0:
                data = client.get_metabolite(
                 model_id=bigg_model_name,
                metabolite_id=metabolite.id,
)

            bigg_charge = data.get("charge")

            if bigg_charge is not None and bigg_charge != metabolite.charge:
                    print(f"Updating metabolite '{metabolite.id}'")
                    print(f" - Current charge: {metabolite.charge}")
                    print(f" - BiGG charge   : {bigg_charge}")
                    metabolite.charge = bigg_charge
                    updated_count += 1
            else:
                print(f"Failed to retrieve data for '{metabolite.id}', Skipping update.")

    print(f"\nTotal metabolites updated: {updated_count}")
    return updated_count


def update_metabolite_info(non_curated_model, curated_model):
    """
    Update the charge and formula of metabolites in the non-curated model based on the curated model.

    Parameters:
    - non_curated_model: cobra.Model
      The non-curated model to update.
    - curated_model: cobra.Model
      The curated model with correct metabolite information.
      
    Returns:
    - updated_model: cobra.Model
      The non-curated model with updated metabolite information.
    """
    # Create a copy of the non-curated model
    copy_of_model = non_curated_model.copy()
    # Create a copy of the curated model
    copy_of_model1 = curated_model.copy()

    # Iterate through metabolites in the non-curated model
    for metabolite in copy_of_model.metabolites:
        # Check if the metabolite exists in the curated model
        if metabolite.id in copy_of_model1.metabolites:
            # Find the corresponding metabolite in the curated model
            curated_metabolite = copy_of_model1.metabolites.get_by_id(metabolite.id)
            # Update the charge and formula of the non-curated metabolite
            metabolite.charge = curated_metabolite.charge
            metabolite.formula = curated_metabolite.formula
        else:
            print(f"Metabolite '{metabolite.id}' not found in the curated model.")
    
    return copy_of_model


def add_missing_reactions(non_curated_model, curated_model):
    """
    Add missing reactions from the curated model to the non-curated model.

    Parameters:
    - non_curated_model: cobra.Model
      The non-curated model to update.
    - curated_model: cobra.Model
      The curated model with the complete set of reactions.
      
    Returns:
    - updated_model: cobra.Model
      The non-curated model with added reactions from the curated model.
    """
    # Create a copy of the non-curated model
    updated_model = non_curated_model.copy()

    # Iterate through reactions in the curated model
    for reaction in curated_model.reactions:
        # Check if the reaction exists in the non-curated model
        if reaction.id not in updated_model.reactions:
            # Add the reaction to the non-curated model
            updated_model.add_reactions([reaction.copy()])
            print(f"Reaction '{reaction.id}' was added to the non-curated model.")
        else:
            pass

    # Optimize the updated model
    solution = updated_model.optimize()
    print(f'Biomass reaction flux after adding reactions: {solution.objective_value}')

    # Verify the addition of reactions
    for reaction in curated_model.reactions:
        if reaction.id not in updated_model.reactions:
            print(f"Reaction '{reaction.id}' was not added correctly.")
    
    return updated_model



def add_missing_metabolites(non_curated_model, curated_model):
    """
    Add missing metabolites from the curated model to the non-curated model.

    Parameters:
    - non_curated_model: cobra.Model
      The non-curated model to update.
    - curated_model: cobra.Model
      The curated model with the complete set of metabolites.
      
    Returns:
    - updated_model: cobra.Model
      The non-curated model with added metabolites from the curated model.
    """
    # Create a copy of the non-curated model
    updated_model = non_curated_model.copy()

    # Iterate through metabolites in the curated model
    for metabolite in curated_model.metabolites:
        # Check if the metabolite exists in the non-curated model
        if metabolite.id not in updated_model.metabolites:
            # Create a new metabolite object
            new_metabolite = Metabolite(
                id=metabolite.id,             # Metabolite ID
                name=metabolite.name,         # Metabolite Name
                formula=metabolite.formula,   # Chemical Formula
                compartment=metabolite.compartment, # Compartment (e.g., cytoplasm)
            )

            # Add additional properties
            new_metabolite.charge = metabolite.charge
            new_metabolite.annotation = metabolite.annotation

            # Add the new metabolite to the non-curated model
            updated_model.add_metabolites([new_metabolite])
            print(f"Metabolite '{metabolite.id}' was added to the non-curated model.")
        else:
            pass

    return updated_model