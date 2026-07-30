# TODO rewrite the printing functions and create a new function that returns the information as a dictionary or pandas dataframe for easier manipulation and analysis.


import pandas as pd
from cobra import Model


def find_reactions(
    model: Model,
    search_term: str,
) -> pd.DataFrame:
    records = []

    for reaction in model.reactions:
        if search_term.lower() in reaction.id.lower():
            records.append(
                {
                    "id": reaction.id,
                    "name": reaction.name,
                    "equation": reaction.reaction,
                    "lower_bound": reaction.lower_bound,
                    "upper_bound": reaction.upper_bound,
                    "genes": sorted(g.id for g in reaction.genes),
                    "annotation": reaction.annotation,
                }
            )

    return pd.DataFrame.from_records(records)


def find_metabolites(model, search_word):
    """
    Searches for metabolites in the model whose ID contains the search_word.
    Prints detailed information including related reactions and associated genes.
    
    Parameters:
    - model: COBRApy model object
    - search_word: string to search for in metabolite IDs
    """
    found = False
    for metabolite in model.metabolites:
        if search_word in metabolite.id:
            found = True
            # Print metabolite basic info
            print(f"\n Metabolite: {metabolite.id}")
            print(f" - Name       : {metabolite.name}")
            print(f" - Formula    : {metabolite.formula}")
            print(f" - Charge     : {metabolite.charge}")
            print(f" - Compartment: {metabolite.compartment}")
            print(f" - Annotations: {metabolite.annotation}")
            
            # Get related reactions
            related_reactions = list(metabolite.reactions)

            # Get genes related to the reactions
            related_genes = set()
            for reaction in related_reactions:
                related_genes.update(reaction.genes)

            # Print related reaction and gene IDs
            print(f" - Related Reactions: {', '.join(r.id for r in related_reactions)}")
            print(f" - Associated Genes : {', '.join(g.id for g in related_genes)}")
        if not found:
            print(f"No metabolites found with ID containing '{search_word}'")



def reaction_details(model, reaction_id):
    """
    Prints detailed information about a reaction in the model.

    Parameters:
    - model: COBRApy model object
    - reaction_id: string, ID of the reaction (e.g., 'NOR_syn_1')
    """
    try:
        reaction = model.reactions.get_by_id(reaction_id)
    except KeyError:
        print(f"Reaction '{reaction_id}' not found in the model.")
        return

    print(f"\nReaction ID   : {reaction.id}")
    print(f"Name          : {reaction.name}")
    print(f"Equation      : {reaction.reaction}")
    print(f"Lower Bound   : {reaction.lower_bound}")
    print(f"Upper Bound   : {reaction.upper_bound}")

    print("\nMetabolites and Stoichiometry:")
    net_charge = 0
    for metabolite, coefficient in reaction.metabolites.items():
        print(f" - {metabolite.id:<15}: {coefficient:>6}  "
              f"Name: {metabolite.name:<50} "
              f"Charge: {metabolite.charge:>3}  "
              f"Formula: {metabolite.formula}")
        net_charge += coefficient * (metabolite.charge if metabolite.charge else 0)

    print(f"\nSum of Charge Balance: {net_charge}")

    print("\nAssociated Genes:")
    if reaction.genes:
        for gene in reaction.genes:
            print(f" - {gene.id}")
    else:
        print(" - None")




def gene_reaction_details(model, gene_id):
    """
    Prints information about a gene and all reactions associated with it.

    Parameters:
    - model: COBRApy model object
    - gene_id: string, ID of the gene (e.g., 'AAFOLC_02510')
    """
    try:
        gene = model.genes.get_by_id(gene_id)
    except KeyError:
        print(f"Gene '{gene_id}' not found in the model.")
        return

    print(f"\nGene ID   : {gene.id}")
    print(f"Name      : {gene.name}\n")

    print("Reactions Associated with the Gene:")
    for reaction in gene.reactions:
        print(f"\n- Reaction ID   : {reaction.id}")
        print(f"  Name          : {reaction.name}")
        print(f"  Equation      : {reaction.reaction}")
        print(f"  Bounds        : [{reaction.lower_bound}, {reaction.upper_bound}]")
        
        print("  Metabolites:")
        for met, coeff in reaction.metabolites.items():
            print(f"    {met.id:<15}: {coeff:>6}")




