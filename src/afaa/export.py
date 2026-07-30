def build_metabolite_summary(model, summary, file_path):
    """
    Create a dataframe and an excel file for the metabolite.summary function of cobrapy

    Parameters:
    - model: COBRApy model object
    - summary: COBRApy summary function output
    - metabolite: metabolite object
    """

    # Extracting the data for file naming
    year = time.strftime("%Y")[2:4]
    timestr = time.strftime("%m%d")

    # Extract the producing and consuming fluxes
    producing_flux_df = summary.producing_flux
    consuming_flux_df = summary.consuming_flux

    # Add a 'type' column to distinguish between producing and consuming
    producing_flux_df['type'] = 'producing'
    consuming_flux_df['type'] = 'consuming'

    # Combine both DataFrames
    df_summary = pd.concat([producing_flux_df, consuming_flux_df])
    df_summary_sorted = df_summary.sort_values(by='flux', key=abs, ascending=False)

    df_summary_sorted['reaction_name'] = df_summary_sorted.index.map(lambda x: model.reactions.get_by_id(x).name)

    # Add a new column for the reaction formulas
    df_summary_sorted['reaction_formula'] = df_summary_sorted.index.map(lambda x: model.reactions.get_by_id(x).reaction)
    df_summary_sorted['reaction_genes'] = df_summary_sorted.index.map(lambda x: [gene.id for gene in model.reactions.get_by_id(x).genes])

    return df_summary_sorted.to_excel(file_path, index=False)


def export_reactions_to_excel(model, file_path):
    """
    Export reaction details from the model to an Excel file.

    Parameters:
    - model: cobra.Model
      The metabolic model from which reactions will be extracted.
    - file_path: str
      The file path where the reaction data will be saved as an Excel file.
      
    Returns:
    - None
    """
    # Create an empty DataFrame to store reaction data
    df_reactions = pd.DataFrame(columns=[
        'reaction_id', 'reaction_name', 'reaction_equation', 
        'reaction_lower_bound', 'reaction_upper_bound', 
        'reaction_gene', 'reaction_annotation'
    ])

    # Iterate over all reactions in the model and populate the DataFrame
    for reaction in model.reactions:
        # Create a DataFrame for the current reaction
        reaction_data = pd.DataFrame([{
            "reaction_id": reaction.id,
            "reaction_name": reaction.name,
            "reaction_equation": reaction.reaction,
            "reaction_lower_bound": reaction.lower_bound,
            "reaction_upper_bound": reaction.upper_bound,
            "reaction_gene": reaction.gene_reaction_rule,
            "reaction_annotation": reaction.annotation
        }])
        
        # Concatenate the current reaction's DataFrame to the main DataFrame
        df_reactions = pd.concat([df_reactions, reaction_data], ignore_index=True)

    # Export the DataFrame to an Excel file
    df_reactions.to_excel(file_path, index=False)
    print(f"Reaction data has been exported to {file_path}")


def export_metabolites_to_excel(model, file_path):
    """
    Export metabolite details from the model to an Excel file.

    Parameters:
    - model: cobra.Model
      The metabolic model from which metabolites will be extracted.
    - file_path: str
      The file path where the metabolite data will be saved as an Excel file.
      
    Returns:
    - None
    """
    # Create an empty DataFrame to store metabolite data
    df_metabolites = pd.DataFrame(columns=[
        'metabolite_id', 'metabolite_name', 'metabolite_formula', 
        'metabolite_charge', 'related_reactions'
    ])

    # Iterate over all metabolites in the model and populate the DataFrame
    for metabolite in model.metabolites:
        # Create a DataFrame for the current metabolite
        metabolite_data = pd.DataFrame([{
            "metabolite_id": metabolite.id,
            "metabolite_name": metabolite.name,
            "metabolite_formula": metabolite.formula,
            "metabolite_charge": metabolite.charge,
            "related_reactions": list(metabolite.reactions),
        }])
        
        # Concatenate the current metabolite's DataFrame to the main DataFrame
        df_metabolites = pd.concat([df_metabolites, metabolite_data], ignore_index=True)

    # Export the DataFrame to an Excel file
    df_metabolites.to_excel(file_path, index=False)
    print(f"Metabolite data has been exported to {file_path}")


def export_metabolites_from_reaction(model, reaction_id, file_path):
    """
    Export metabolite details from a specific reaction in the model to an Excel file.

    Parameters:
    - model: cobra.Model
      The metabolic model containing the reaction.
    - reaction_id: str
      The ID of the reaction to extract metabolites from.
    - file_path: str
      The file path where the metabolite data will be saved as an Excel file.
      
    Returns:
    - None
    """
    # Create an empty DataFrame to store metabolite data
    df_reaction = pd.DataFrame(columns=['met_id', 'met_name', 'met_coeff', 'met_charge'])

    # Get the reaction from the model
    try:
        reaction = model.reactions.get_by_id(reaction_id)
        
        # Iterate through metabolites and coefficients in the reaction
        for metabolite, coefficient in reaction.metabolites.items():
            print(f"{metabolite.id:<15}: {coefficient:>25}  Name: {metabolite.name:<60}  Charge: {metabolite.charge:>3}  Formula: {metabolite.formula}")
            
            # Create a DataFrame for the current metabolite
            reaction_data = pd.DataFrame([{
                "met_id": metabolite.id,
                "met_name": metabolite.name,
                "met_coeff": coefficient,
                "met_charge": metabolite.charge,
            }])

            # Concatenate the current metabolite's DataFrame to the main DataFrame
            df_reaction = pd.concat([df_reaction, reaction_data], ignore_index=True)

        # Export the DataFrame to an Excel file
        df_reaction.to_excel(file_path, index=False)
        print(f"Metabolite data from reaction '{reaction_id}' has been exported to {file_path}")
    
    except KeyError:
        print(f"Reaction '{reaction_id}' not found in the model.")