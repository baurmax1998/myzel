import yaml
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field, asdict
from typing import Dict


@dataclass
class ResourceMetadata:
    """Metadaten für eine Ressource"""
    technical_id: str
    resource_type: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateMetadata:
    """Metadaten für den State"""
    version: str = "1.0"
    last_sync: str = field(default_factory=lambda: datetime.now().isoformat())
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AppState:
    """Repräsentiert den aktuellen State einer IAC-Anwendung"""
    resources: Dict[str, ResourceMetadata] = field(default_factory=dict)
    metadata: StateMetadata = field(default_factory=StateMetadata)

    def to_dict(self) -> dict:
        """Konvertiert State zu Dictionary für YAML-Serialisierung"""
        return {
            "resources": {
                resource_id: asdict(resource_meta)
                for resource_id, resource_meta in self.resources.items()
            },
            "metadata": asdict(self.metadata)
        }

    @staticmethod
    def from_dict(data: dict) -> "AppState":
        """Erstellt AppState aus Dictionary (z.B. aus YAML geladen)"""
        resources = {}
        for resource_id, resource_data in data.get("resources", {}).items():
            resources[resource_id] = ResourceMetadata(**resource_data)

        metadata_data = data.get("metadata", {})
        metadata = StateMetadata(**metadata_data) if metadata_data else StateMetadata()

        return AppState(resources=resources, metadata=metadata)


class StateManager:
    """Verwaltet Persistierung und Abruf des aktuellen IAC-States"""

    def __init__(self, config_file_path: str):
        self.config_path = Path(config_file_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> AppState:
        """YAML-Config laden - enthält Mapping von resource_id -> ResourceMetadata"""
        if not self.config_path.exists():
            return AppState()

        try:
            with open(self.config_path, 'r') as f:
                state_dict = yaml.safe_load(f)
                return AppState.from_dict(state_dict) if state_dict else AppState()
        except Exception as e:
            raise Exception(f"Fehler beim Laden der State-Datei: {e}")

    def save_state(self, state: AppState) -> None:
        """State in YAML speichern"""
        try:
            state.metadata.last_sync = datetime.now().isoformat()
            state_dict = state.to_dict()
            with open(self.config_path, 'w') as f:
                yaml.dump(state_dict, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise Exception(f"Fehler beim Speichern der State-Datei: {e}")

    def update_resource(self, resource_id: str, data: dict) -> None:
        """einzelne Ressource updaten"""
        state = self.load_state()
        # Konvertiere dict zu ResourceMetadata
        resource_meta = ResourceMetadata(**data)
        resource_meta.updated_at = datetime.now().isoformat()
        state.resources[resource_id] = resource_meta
        self.save_state(state)

    def delete_resource(self, resource_id: str) -> None:
        """Ressource aus Config entfernen"""
        state = self.load_state()
        if resource_id in state.resources:
            del state.resources[resource_id]
            self.save_state(state)

    def get_resource(self, resource_id: str) -> Optional[ResourceMetadata]:
        """einzelne Ressource abrufen"""
        state = self.load_state()
        return state.resources.get(resource_id)

    def get_version(self) -> str:
        """Hole die aktuelle Version aus den Metadaten"""
        state = self.load_state()
        return state.metadata.version

    def set_version(self, version: str) -> None:
        """Setze die neue Version in den Metadaten"""
        state = self.load_state()
        state.metadata.version = version
        self.save_state(state)
