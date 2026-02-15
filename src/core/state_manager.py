import yaml
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Any


class StateManager:
    """Verwaltet Persistierung und Abruf des aktuellen IAC-States"""

    def __init__(self, config_file_path: str):
        self.config_path = Path(config_file_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict:
        """YAML-Config laden"""
        if not self.config_path.exists():
            return {
                "resources": {},
                "metadata": {
                    "version": "1.0",
                    "last_sync": datetime.now().isoformat(),
                }
            }

        try:
            with open(self.config_path, 'r') as f:
                state = yaml.safe_load(f)
                return state if state else {"resources": {}, "metadata": {}}
        except Exception as e:
            raise Exception(f"Fehler beim Laden der State-Datei: {e}")

    def save_state(self, state: dict) -> None:
        """State in YAML speichern"""
        try:
            state["metadata"]["last_sync"] = datetime.now().isoformat()
            with open(self.config_path, 'w') as f:
                yaml.dump(state, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise Exception(f"Fehler beim Speichern der State-Datei: {e}")

    def update_resource(self, resource_id: str, data: dict) -> None:
        """einzelne Ressource updaten"""
        state = self.load_state()
        if "resources" not in state:
            state["resources"] = {}
        state["resources"][resource_id] = data
        self.save_state(state)

    def delete_resource(self, resource_id: str) -> None:
        """Ressource aus Config entfernen"""
        state = self.load_state()
        if "resources" in state and resource_id in state["resources"]:
            del state["resources"][resource_id]
            self.save_state(state)

    def get_resource(self, resource_id: str) -> Optional[dict]:
        """einzelne Ressource abrufen"""
        state = self.load_state()
        return state.get("resources", {}).get(resource_id)

    def get_version(self) -> str:
        """Hole die aktuelle Version aus den Metadaten"""
        state = self.load_state()
        return state.get("metadata", {}).get("version", "1.0")

    def set_version(self, version: str) -> None:
        """Setze die neue Version in den Metadaten"""
        state = self.load_state()
        if "metadata" not in state:
            state["metadata"] = {}
        state["metadata"]["version"] = version
        self.save_state(state)
