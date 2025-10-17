# testlib/adapters/rest_adapter.py
import requests
from typing import Dict, Any

class RESTAdapter:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def create(self, resource_type: str, data: Dict) -> str:
        resp = requests.post(f"{self.base_url}/{resource_type}", json=data)
        resp.raise_for_status()
        return resp.json()["id"]  # assume API returns {"id": "...", ...}

    def read(self, resource_type: str, resource_id: str) -> Dict:
        resp = requests.get(f"{self.base_url}/{resource_type}/{resource_id}")
        resp.raise_for_status()
        return resp.json()

    def update(self, resource_type: str, resource_id: str, data: Dict) -> Dict:
        resp = requests.put(f"{self.base_url}/{resource_type}/{resource_id}", json=data)
        resp.raise_for_status()
        return resp.json()

    def delete(self, resource_type: str, resource_id: str) -> bool:
        resp = requests.delete(f"{self.base_url}/{resource_type}/{resource_id}")
        return resp.status_code in (200, 204)