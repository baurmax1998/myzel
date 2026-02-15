import os
from pathlib import Path
from packaging import version
from datetime import datetime
from typing import Optional

from .state_manager import StateManager
from .diff_engine import DiffEngine


def deploy(
        app,
        config_dir: str = "/Users/ba22036/PycharmProjects/myzel/src/examples/config",
        dry_run: bool = False,
) -> dict:
    """
    Deploy-Funktion für AwsApp

    Args:
        app: AwsApp-Instanz mit name, env und constructs
        config_dir: Verzeichnis für YAML-Dateien
        dry_run: Wenn True, nur zeigen was passieren würde

    Returns:
        dict mit Deploy-Ergebnissen
    """
    try:
        # Erstelle config_dir falls nicht vorhanden
        os.makedirs(config_dir, exist_ok=True)

        # Lade oder erstelle State
        config_file = os.path.join(config_dir, f"app_{app.name}.yaml")
        state_manager = StateManager(config_file)

        # Erstelle ein Dict mit Ressourcen für die DiffEngine
        # resource_id wird von der Ressource selbst bereitgestellt
        resources_dict = {}
        for construct in app.constructs:
            try:
                resource_id = construct.get_resource_id()
            except (AttributeError, NotImplementedError):
                # Fallback auf Index falls get_resource_id nicht implementiert
                resource_id = str(len(resources_dict))
            resources_dict[resource_id] = construct

        # Lade aktuellen State - enthält Mapping von resource_id -> technical_id
        state = state_manager.load_state()
        if "resources" not in state:
            state["resources"] = {}

        # Synchronisiere neue Ressourcen in den State (nur wenn sie nicht existieren)
        # State speichert: resource_id, technical_id, resource_type
        for resource_id, resource in resources_dict.items():
            if resource_id not in state["resources"]:
                # Neue Ressource - initialisiere das Mapping
                # technical_id wird aus bucket_name oder aws_id ermittelt
                technical_id = getattr(resource, 'bucket_name', None) or getattr(resource, 'aws_id',
                                                                                 None) or resource_id
                state["resources"][resource_id] = {
                    "resource_id": resource_id,
                    "technical_id": technical_id,
                    "resource_type": resource.__class__.__name__
                }

        state_manager.save_state(state)

        # Initialisiere DiffEngine
        diff_engine = DiffEngine(state_manager, resources_dict)

        # Berechne Diffs
        print(f"\n{'=' * 60}")
        print(f"Deploying application: {app.name}")
        print(f"{'=' * 60}\n")

        diffs = diff_engine.calculate_diffs()

        if not diffs:
            print("✓ Keine Änderungen gefunden. Alles ist synchron.")
            return {
                "status": "success",
                "message": "No changes",
                "diffs_count": 0,
                "diffs": [],
                "applied": []
            }

        # Zeige Diffs
        print("Detected changes:")
        print("-" * 60)
        for diff in diffs:
            print(f"  {diff}")

        # Wende Diffs an
        print(f"\n{'Dry-Run' if dry_run else 'Applying'} changes...")
        print("-" * 60)

        apply_results = diff_engine.apply_diffs(diffs, dry_run=dry_run)

        # Zeige Ergebnisse
        for result in apply_results["applied"]:
            status_symbol = "→" if dry_run else "✓"
            print(f"  {status_symbol} {result['message']}")

        for result in apply_results["failed"]:
            print(f"  ✗ FAILED: {result['error']}")

        # Speichere neuen State
        if not dry_run and apply_results["applied"]:
            state = state_manager.load_state()

            # Aktualisiere Ressourcen im State - speichere Mapping
            if "resources" not in state:
                state["resources"] = {}

            for construct in app.constructs:
                try:
                    resource_id = construct.get_resource_id()
                except (AttributeError, NotImplementedError):
                    resource_id = str(app.constructs.index(construct))

                # Speichere Mapping: resource_id, technical_id, resource_type
                # technical_id wird aus bucket_name (S3) oder aws_id ermittelt
                technical_id = getattr(construct, 'bucket_name', None) or getattr(construct, 'aws_id',
                                                                                  None) or resource_id

                state["resources"][resource_id] = {
                    "resource_id": resource_id,
                    "technical_id": technical_id,
                    "resource_type": construct.__class__.__name__
                }

            # Erhöhe Version
            current_version = state.get("metadata", {}).get("version", "1.0")
            try:
                v = version.parse(current_version)
                # Erhöhe die Patch-Version
                new_version = f"{v.major}.{v.minor}.{v.micro + 1}"
            except Exception:
                new_version = "1.0.1"

            state["metadata"]["version"] = new_version
            print(f"\n✓ Version updated: {current_version} -> {new_version}")

            state_manager.save_state(state)
            print(f"✓ State saved to: {config_file}")

        print(f"\n{'=' * 60}")
        print(f"Deploy result: {len(apply_results['applied'])} applied, {len(apply_results['failed'])} failed")
        print(f"{'=' * 60}\n")

        return {
            "status": "success" if not apply_results["failed"] else "partial",
            "diffs_count": len(diffs),
            "applied": apply_results["applied"],
            "failed": apply_results["failed"],
            "dry_run": dry_run,
            "config_file": config_file
        }

    except Exception as e:
        print(f"\n✗ Deploy failed with error: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }
