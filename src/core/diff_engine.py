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
        """Vergleicht aktuellen State mit desired State"""
        diffs = []
        state = self.state_manager.load_state()
        config_resources = state.get("resources", {})

        # 1. Iterate über alle Ressourcen in Config
        for resource_id, config_data in config_resources.items():
            if resource_id not in self.resources:
                continue

            resource = self.resources[resource_id]

            # 2. Aktuellen AWS-State abrufen
            try:
                actual_state = resource.read()
            except Exception:
                # Wenn read() fehlschlägt, nehmen wir an die Ressource existiert nicht
                actual_state = None

            # 3. Vergleichen
            if actual_state is None:
                # Ressource in Config, aber nicht in AWS -> CREATE
                diffs.append(
                    Diff(
                        resource_id=resource_id,
                        resource_type=config_data.get("resource_type", "Unknown"),
                        diff_type=DiffType.CREATE
                    )
                )
            else:
                # Eigenschaften vergleichen
                config_props = config_data.get("properties", {})
                for prop, desired_val in config_props.items():
                    actual_val = actual_state.get(prop)
                    if actual_val != desired_val:
                        diffs.append(
                            Diff(
                                resource_id=resource_id,
                                resource_type=config_data.get("resource_type", "Unknown"),
                                diff_type=DiffType.UPDATE,
                                field=prop,
                                current_value=actual_val,
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
                        resource.update(diff.field, diff.desired_value)
                        results["applied"].append({
                            "diff": str(diff),
                            "status": "SUCCESS",
                            "message": f"Updated {diff.resource_type} '{diff.resource_id}'"
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
