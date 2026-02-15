from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional, List
from datetime import datetime


class DiffType(Enum):
    """Enum für Diff-Typen"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class Diff:
    """Repräsentiert eine Änderung zwischen desired und actual State"""
    resource_id: str
    resource_type: str
    diff_type: DiffType
    field: Optional[str] = None
    current_value: Any = None
    desired_value: Any = None

    def __str__(self) -> str:
        if self.diff_type == DiffType.CREATE:
            return f"[{self.diff_type.value}] {self.resource_type} '{self.resource_id}'"
        elif self.diff_type == DiffType.DELETE:
            return f"[{self.diff_type.value}] {self.resource_type} '{self.resource_id}'"
        else:  # UPDATE
            return f"[{self.diff_type.value}] {self.resource_type} '{self.resource_id}' - {self.field}: {self.current_value} -> {self.desired_value}"


class DiffEngine:
    """Vergleicht desired State mit actual State und wendet Diffs an"""

    def __init__(self, state_manager, resources: dict):
        """
        state_manager: StateManager-Instanz
        resources: Dict mapping resource_id -> Resource-Objekt
        """
        self.state_manager = state_manager
        self.resources = resources

    def calculate_diffs(self) -> List[Diff]:
        """Vergleicht desired State (Code) mit actual State (AWS via read())"""
        diffs = []
        state = self.state_manager.load_state()
        mapped_resources = state.get("resources", {})

        # 1. Iterate über alle Ressourcen im Code
        for resource_id, resource in self.resources.items():
            # 2. Abrufen ob Ressource bereits getracked ist
            is_tracked = resource_id in mapped_resources

            # 3. Gewünschte Properties aus Code-Ressource abrufen
            desired_properties = {
                k: v for k, v in resource.__dict__.items()
                if not k.startswith('_') and k not in ['s3_client', 'env', 'aws_id', 'resource_id']
            }

            # 4. Aktuellen State von AWS abrufen via read()
            try:
                actual_state = resource.read()
            except Exception:
                actual_state = None

            # 5. Vergleichen
            if actual_state is None:
                # Ressource existiert nicht in AWS mit desired properties
                if is_tracked:
                    # War vorher getracked -> UPDATE (Properties wurden geändert, Ressource muss neu erstellt werden)
                    state = self.state_manager.load_state()
                    mapped_resource = state.get("resources", {}).get(resource_id, {})
                    old_technical_id = mapped_resource.get("technical_id")

                    for prop, desired_val in desired_properties.items():
                        # Für bucket_name: nutze old_technical_id als current_value
                        current_value = old_technical_id if prop == "bucket_name" else None

                        diffs.append(
                            Diff(
                                resource_id=resource_id,
                                resource_type=resource.__class__.__name__,
                                diff_type=DiffType.UPDATE,
                                field=prop,
                                current_value=current_value,
                                desired_value=desired_val
                            )
                        )
                else:
                    # Ist nicht getracked -> neue Ressource -> CREATE
                    diffs.append(
                        Diff(
                            resource_id=resource_id,
                            resource_type=resource.__class__.__name__,
                            diff_type=DiffType.CREATE
                        )
                    )
            else:
                # Ressource existiert in AWS - vergleiche Properties
                for prop, desired_val in desired_properties.items():
                    actual_val = actual_state.get(prop)
                    if actual_val != desired_val:
                        # Für Updates mit technical_id: nutze old_technical_id statt actual_val
                        # (wenn sich der Name geändert hat, können wir nicht mehr auslesen)
                        current_value = actual_val
                        if is_tracked and prop == "bucket_name":
                            # Nutze den stored technical_id als old_value
                            state = self.state_manager.load_state()
                            mapped_resource = state.get("resources", {}).get(resource_id, {})
                            current_value = mapped_resource.get("technical_id")

                        diffs.append(
                            Diff(
                                resource_id=resource_id,
                                resource_type=resource.__class__.__name__,
                                diff_type=DiffType.UPDATE,
                                field=prop,
                                current_value=current_value,
                                desired_value=desired_val
                            )
                        )

        return diffs

    def apply_diffs(self, diffs: List[Diff], dry_run: bool = True) -> dict:
        """Wendet Diffs an oder zeigt sie im Dry-Run-Modus"""
        results = {
            "total": len(diffs),
            "applied": [],
            "failed": [],
            "dry_run": dry_run
        }

        for diff in diffs:
            if diff.resource_id not in self.resources:
                results["failed"].append({
                    "diff": str(diff),
                    "error": f"Ressource {diff.resource_id} nicht gefunden"
                })
                continue

            resource = self.resources[diff.resource_id]

            try:
                if dry_run:
                    results["applied"].append({
                        "diff": str(diff),
                        "status": "DRY_RUN",
                        "message": f"Would {diff.diff_type.value} {diff.resource_type} '{diff.resource_id}'"
                    })
                else:
                    if diff.diff_type == DiffType.CREATE:
                        resource.create()
                        results["applied"].append({
                            "diff": str(diff),
                            "status": "SUCCESS",
                            "message": f"Created {diff.resource_type} '{diff.resource_id}'"
                        })
                    elif diff.diff_type == DiffType.UPDATE:
                        # Hole den alten technical_id aus der YAML für Updates
                        state = self.state_manager.load_state()
                        mapped_resource = state.get("resources", {}).get(diff.resource_id, {})
                        old_technical_id = mapped_resource.get("technical_id")

                        resource.update(diff.field, diff.current_value, diff.desired_value, old_technical_id)
                        results["applied"].append({
                            "diff": str(diff),
                            "status": "SUCCESS",
                            "message": f"Updated {diff.resource_type} '{diff.resource_id}' - {diff.field}: {diff.current_value} -> {diff.desired_value}"
                        })
                    elif diff.diff_type == DiffType.DELETE:
                        resource.delete(diff.resource_id)
                        results["applied"].append({
                            "diff": str(diff),
                            "status": "SUCCESS",
                            "message": f"Deleted {diff.resource_type} '{diff.resource_id}'"
                        })

            except Exception as e:
                results["failed"].append({
                    "diff": str(diff),
                    "error": str(e)
                })

        return results
