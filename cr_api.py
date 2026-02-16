# cr_api.py -- minimal wrapper async pour api.clashroyale.com/v1
import aiohttp
from typing import Optional, Dict, Any, List
from config import CLASH_ROYALE_TOKEN

BASE = "https://api.clashroyale.com/v1"

class CRApiError(Exception):
    pass

class CRClient:
    """Client API Clash Royale utilisant aiohttp en gestion de contexte (async with)."""
    
    def __init__(self, token: str = CLASH_ROYALE_TOKEN):
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None # Sera créé dans __aenter__
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

    # Méthode d'entrée pour 'async with' (crée la session)
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    # Méthode de sortie pour 'async with' (ferme la session)
    async def __aexit__(self, exc_type, exc, tb):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = BASE + path
        
        if self.session is None:
            # Sécurité si on oublie le 'async with'
            raise RuntimeError("CRClient doit être utilisé dans un bloc 'async with CRClient() as cr:'.")
            
        async with self.session.get(url, headers=self.headers, params=params) as r:
            if r.status == 200:
                return await r.json()
            elif r.status == 404:
                raise CRApiError(f"Not found: {url}")
            elif r.status == 401 or r.status == 403:
                # Si le jeton est mauvais OU si l'IP n'est pas autorisée (Render)
                raise CRApiError("Auth error with Clash Royale API (check token and IP settings on Supercell site)")
            else:
                text = await r.text()
                raise CRApiError(f"CR API error {r.status}: {text}")

    async def get_player(self, tag: str) -> Dict[str, Any]:
        tag = tag.strip("#").upper()
        return await self._get(f"/players/%23{tag}")

    async def get_clan(self, tag: str) -> Dict[str, Any]:
        tag = tag.strip("#").upper()
        return await self._get(f"/clans/%23{tag}")

    async def get_card(self, name: str) -> Dict[str, Any]:
        data = await self._get("/cards")
        name_lower = name.strip().lower()
        for card in data.get("items", data):
            if card.get("name", "").lower() == name_lower:
                return card
        raise CRApiError(f"Card '{name}' not found")
    
    async def get_upcoming_chests(self, tag: str) -> Dict[str, Any]:
        tag = tag.strip("#").upper()
        return await self._get(f"/players/%23{tag}/upcomingchests")

    async def get_battle_log(self, tag: str) -> List[Dict[str, Any]]:
        tag = tag.strip("#").upper()
        return await self._get(f"/players/%23{tag}/battlelog")
    
    async def get_current_river_race(self, tag: str) -> Dict[str, Any]:
        tag = tag.strip("#").upper()
        return await self._get(f"/clans/%23{tag}/currentriverrace") 

    async def get_clan_war_log(self, tag: str) -> List[Dict[str, Any]]:
        tag = tag.strip("#").upper()
        # L'API retourne une liste d'éléments (items)
        data = await self._get(f"/clans/%23{tag}/warlog")
        return data.get('items', [])