#TODO create a function to handle the input dataframe and update the biomass reaction accordingly. 
#This function should take in a dataframe with metabolite IDs and their corresponding coefficients, and update the biomass reaction in the model accordingly.

import pandas as pd
from typing import Literal, Optional

def update_biomass_from_dataframe(model, biomass_df, reaction_id='Growth', id_column='Biomass_equation', coeff_column='normalized_mmol/g'):
    """
    Updates metabolite coefficients in a biomass reaction based on values in a given DataFrame.

    Parameters:
    - model: COBRApy model object
    - biomass_df: pandas DataFrame with metabolite IDs and updated coefficients
    - reaction_id: string, ID of the biomass reaction in the model (default: 'Growth')
    - id_column: string, column name in the DataFrame containing metabolite IDs
    - coeff_column: string, column name in the DataFrame containing new coefficient values

    Returns:
    - int: number of metabolites successfully updated
    """
    reaction = model.reactions.get_by_id(reaction_id)
    update_count = 0

    for element in biomass_df[id_column]:
        found = False
        for metabolite, coefficient in reaction.metabolites.items():
            if element == metabolite.id:
                found = True
                # Get the updated coefficient from the DataFrame
                new_coeff = biomass_df.loc[biomass_df[id_column] == element, coeff_column].values[0]

                print(f'\n✔ Updating {element}')
                print(f' - Original coefficient in model : {coefficient}')
                print(f' - New coefficient from DataFrame: {new_coeff}')

                # Update metabolite coefficient (replace, not add)
                reaction.add_metabolites({metabolite: new_coeff}, combine=False)
                updated_coefficient = reaction.metabolites[metabolite]

                print(f' - Updated coefficient           : {updated_coefficient}')

                # Test optimization
                solution = model.slim_optimize()
                print(f' - Growth rate after update      : {solution}')

                update_count += 1
                break

        if not found:
            print(f'⚠ Metabolite {element} not found in biomass reaction.')

    print(f"\n Total metabolites updated: {update_count}")
    return update_count


def find_missing_biomass_metabolites(
    model,
    biomass_df: pd.DataFrame,
    reaction_id: str = "Growth",
    source: Literal["Dataframe", "Model"] = "Dataframe",
    id_column: str = "Biomass_equation",
    coeff_column: str = "normalized_mmol/g",
    name_column: str = "Unnamed: 1",
    output_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Compare biomass metabolites between a COBRApy biomass reaction
    and a biomass-composition DataFrame.

    Parameters
    ----------
    model
        COBRApy model object.

    biomass_df
        DataFrame containing biomass metabolite information.

    reaction_id
        ID of the biomass reaction.

    source
        Direction of the comparison:

        - "Dataframe": metabolites listed in the DataFrame but absent
          from the model biomass reaction.
        - "Model": metabolites present in the model biomass reaction
          but absent from the DataFrame.

    id_column
        Column containing metabolite IDs.

    coeff_column
        Column containing biomass coefficients.

    name_column
        Column containing metabolite names.

    output_path
        Optional path for exporting the result to Excel.

    Returns
    -------
    pandas.DataFrame
        Missing metabolites with their IDs, names, and coefficients.
    """

    if source not in {"Dataframe", "Model"}:
        raise ValueError(
            "source must be either 'Dataframe' or 'Model'."
        )

    required_columns = {id_column}

    if source == "Dataframe":
        required_columns.update({coeff_column, name_column})

    missing_columns = required_columns - set(biomass_df.columns)

    if missing_columns:
        raise KeyError(
            f"Missing required DataFrame columns: {sorted(missing_columns)}"
        )

    try:
        reaction = model.reactions.get_by_id(reaction_id)
    except KeyError as exc:
        raise KeyError(
            f"Reaction '{reaction_id}' was not found in the model."
        ) from exc

    # Remove missing IDs and convert them to strings.
    dataframe_ids = set(
        biomass_df[id_column].dropna().astype(str)
    )

    model_metabolites = {
        metabolite.id: metabolite
        for metabolite in reaction.metabolites
    }

    model_ids = set(model_metabolites)

    results = []

    if source == "Dataframe":
        # IDs in the DataFrame but absent from the model biomass reaction.
        missing_ids = dataframe_ids - model_ids

        missing_rows = biomass_df[
            biomass_df[id_column].astype(str).isin(missing_ids)
        ]

        for _, row in missing_rows.iterrows():
            results.append(
                {
                    "metabolite_id": row[id_column],
                    "metabolite_name": row[name_column],
                    "coefficient": row[coeff_column],
                }
            )

        message = "Metabolites in DataFrame but not in model biomass"

    else:
        # IDs in the model biomass reaction but absent from the DataFrame.
        missing_ids = model_ids - dataframe_ids

        for metabolite_id in sorted(missing_ids):
            metabolite = model_metabolites[metabolite_id]

            results.append(
                {
                    "metabolite_id": metabolite.id,
                    "metabolite_name": metabolite.name,
                    "coefficient": reaction.metabolites[metabolite],
                }
            )
        message = "Metabolites in model biomass but not in DataFrame"

    result_df = pd.DataFrame(
        results,
        columns=[
            "metabolite_id",
            "metabolite_name",
            "coefficient",
        ],
    )

    print(f"{message}: {len(result_df)}")

    if output_path is not None:
        result_df.to_excel(output_path, index=False)
        print(f"Result saved to: {output_path}")

    return result_df


def compare_biomass_metabolites_between_models(model_a, model_b,
                                               reaction_id_a='Growth',
                                               reaction_id_b='BIOMASS_KT2440_WT3'):
    """
    Compares biomass reactions from two models and returns metabolites present in model_b but missing in model_a.

    Parameters:
    - model_a: COBRApy model object (reference model)
    - model_b: COBRApy model object (comparison model)
    - reaction_id_a: biomass reaction ID in model_a (default: 'Growth')
    - reaction_id_b: biomass reaction ID in model_b (default: 'BIOMASS_KT2440_WT3')

    Returns:
    - DataFrame containing the list of metabolites not found in model_a's biomass reaction
    """
    reaction_a = model_a.reactions.get_by_id(reaction_id_a)
    reaction_b = model_b.reactions.get_by_id(reaction_id_b)

    metabolites_not_found = []

    for met_b in reaction_b.metabolites:
        if met_b.id not in {met.id for met in reaction_a.metabolites}:
            metabolites_not_found.append({
                'metabolite_id': met_b.id,
                'metabolite_name': met_b.name
            })

    df_missing = pd.DataFrame(metabolites_not_found)
    print(f"Number of metabolites not found in '{reaction_id_a}': {len(df_missing)}")
    return df_missing


def update_gam(model, reaction_id='Growth', gam_dict_1=None, gam_dict_2=None, verbose=True):
    """
    Updates the GAM-related metabolite coefficients in the biomass reaction and optimizes the model.

    Parameters:
    - model: COBRApy model object
    - reaction_id: string, ID of the biomass reaction (default: 'Growth')
    - gam_dict_1: dict, metabolites and coefficients (usually negative side)
    - gam_dict_2: dict, metabolites and coefficients (usually positive side)
    - verbose: bool, whether to print details during update

    Returns:
    - float: optimized objective value (growth rate)
    """
    if gam_dict_1 is None:
        gam_dict_1 = {'atp_c': -49.0, 'h2o_c': -49.0}
    if gam_dict_2 is None:
        gam_dict_2 = {'adp_c': 49.0, 'pi_c': 49.0, 'h_c': 49.0}

    reaction = model.reactions.get_by_id(reaction_id)

    for gam_dict in [gam_dict_1, gam_dict_2]:
        for met_id, new_coeff in gam_dict.items():
            metabolite = model.metabolites.get_by_id(met_id)
            if metabolite in reaction.metabolites:
                old_coeff = reaction.metabolites[metabolite]
                reaction.add_metabolites({metabolite: new_coeff - old_coeff})
                if verbose:
                    print(f'Updated {met_id}: {old_coeff} → {new_coeff}')
            else:
                if verbose:
                    print(f" Metabolite {met_id} not found in biomass reaction.")

    # Re-optimize the model
    solution = model.slim_optimize()
    if verbose:
        print(f"\nOptimal growth rate after GAM update: {solution}")

    return solution