def check_model_mass_balance(model):
    """
    Checks for mass or charge imbalances in the reactions of a COBRA model.

    Parameters:
    - model: COBRApy model object

    Prints:
    - The number of imbalanced reactions
    - Each reaction's ID and its imbalance details
    """
    imbalanced_reactions = cobra.manipulation.validate.check_mass_balance(model)

    print(f"\nNumber of imbalanced reactions: {len(imbalanced_reactions)}")

    for reaction, imbalance in imbalanced_reactions.items():
        print(f"Reaction ID: {reaction.id}, Imbalance: {imbalance}")