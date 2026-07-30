import requests


class BiggClient:
    def __init__(self, 
                 base_url: str ='http://bigg.ucsd.edu/api/v2',
                 timeout: int = 15,
                 session: requests.Session = None):
        
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def get_reaction(self, reaction_id: str) -> dict:
        response = self.session.get(
            f"{self.base_url}/universal/reactions/{reaction_id}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
    def get_metabolite(
        self,
        model_id: str,
        metabolite_id: str,
    ) -> dict:
        response = self.session.get(
            f"{self.base_url}/models/{model_id}/metabolites/{metabolite_id}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

