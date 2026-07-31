from cobra import Model

from afaa.inspection import reaction_details
from afaa.flux import get_active_reactions
from afaa.biomass import update_gam
from afaa.phpp import phpp as run_phpp


class Workbench:
    def __init__(self, model: Model):
        self.model = model

    def reaction_details(self, reaction_id: str):
        return reaction_details(self.model, reaction_id)

    def get_active_reactions(self, solution, threshold=1e-9):
        return get_active_reactions(
            self.model,
            solution,
            threshold=threshold,
        )

    def update_gam(self, reaction_id="Growth", **kwargs):
        return update_gam(
            self.model,
            reaction_id=reaction_id,
            **kwargs,
        )

    def phpp(
        self,
        h2_reaction_id: str = "EX_h2_e",
        o2_reaction_id: str = "EX_o2_e",
        **kwargs,
    ):
        return run_phpp(
            self.model,
            h2_reaction_id=h2_reaction_id,
            o2_reaction_id=o2_reaction_id,
            **kwargs,
        )
