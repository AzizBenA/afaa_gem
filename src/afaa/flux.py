def reaction_flux(objective_rxn, model, reaction_id):
    """
    Optimizes the model and checks the flux through a specified reaction.

    Parameters:
    - model: COBRApy model object
    - reaction_id: string, ID of the reaction to check

    Returns:
    - flux_value: float or None
    """
    model.objective = objective_rxn
    solution = model.optimize()

    if solution.status == 'optimal':
        # Check if the reaction ID exists in the solution
        if reaction_id not in solution.fluxes:
            print(f"Reaction '{reaction_id}' not found in the model.")
            return None

        # Retrieve flux value
        flux_value = solution.fluxes[reaction_id]
        if flux_value != 0:
            print(f"The reaction '{reaction_id}' has a flux of {flux_value:.3f} mmol/gDW/hr.")
        else:
            print(f"There is no flux through the reaction '{reaction_id}'.")
        
        return flux_value
    else:
        print("Optimization was not successful. Check model constraints or objective function.")
        return None


def get_active_reactions_for_metabolite(model, solution, metabolite_id, flux_threshold=0.5):
    """
    Returns a list of reactions involving a specific metabolite that carry significant flux.

    Parameters:
    - model: COBRApy model object
    - solution: COBRApy solution object (after optimization)
    - metabolite_id: string, ID of the metabolite (e.g. 'h2_c')
    - flux_threshold: float, minimum absolute flux to include (default 0.5)

    Returns:
    - List of [reaction name, reaction ID, equation, flux] for each active reaction
    """
    try:
        metabolite = model.metabolites.get_by_id(metabolite_id)
    except KeyError:
        print(f" Metabolite '{metabolite_id}' not found in model.")
        return []

    active_reactions = [
        [rxn.name, rxn.id, rxn.reaction, solution.fluxes[rxn.id]]
        for rxn in metabolite.reactions
        if abs(solution.fluxes[rxn.id]) > flux_threshold
    ]

    return active_reactions 


def get_active_reactions(model, solution,threshold=1e-9):

    # Create a list to store active reactions
    active_reactions = []

    for rxn in model.reactions:
        if  abs(solution.fluxes[rxn.id]) > threshold:
            active_reactions.append([rxn.name, rxn.id, solution.fluxes[rxn.id]])

    df_active_rxn = pd.DataFrame(active_reactions, columns=['Reaction Name', 'Reaction ID',  'Flux Value'])
    return df_active_rxn