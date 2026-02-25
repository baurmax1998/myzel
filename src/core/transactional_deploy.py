from datetime import datetime
from pathlib import Path
from typing import Optional

from src.model import MyzelApp, Resources, IacMapping, ResourceMapping, DeploymentProgress
from src.model.registry import get_resource_class, get_resource_type


class TransactionalDeploymentContext:
    """Context manager for transactional resource deployment"""

    def __init__(self, app: MyzelApp, config_dir: Path = Path("config")):
        self.app = app
        self.config_dir = config_dir
        self.config_file = config_dir / f"app_{app.name}.yaml"

        # Track deployment state
        self.new_deployed_state: dict[str, Resources] = {}
        self.new_iac_mapping = IacMapping()
        self.deployment_progress = DeploymentProgress()
        self.deployment_failed = False

    def add_resource(self, resource_id: str, resource: Resources) -> None:
        """Add and immediately deploy a resource"""

        # Check if resource exists in current state
        resource_type = get_resource_type(resource)
        resource_class_name = resource.__class__.__name__

        if resource_id in self.app.current_state:
            deployed = self.app.current_state[resource_id]
            tech_id = self.app.current_config.resources[resource_id].tech_id

            # Check if update is needed
            if resource != deployed:
                print(f"[DEPLOY] Updating: {resource_id} ({resource_class_name})")
                new_tech_id = deployed.update(tech_id, resource)
                tech_id = new_tech_id if new_tech_id is not None else tech_id
                resource.set_tech_id(tech_id)
                print(f"[DEPLOY] ✓ Updated: {resource_id} → {tech_id}")
            else:
                print(f"[DEPLOY] No changes: {resource_id} ({resource_class_name})")
                # Set tech_id from deployed state
                resource.set_tech_id(tech_id)
        else:
            # Create new resource
            print(f"[DEPLOY] Creating: {resource_id} ({resource_class_name})")
            tech_id = resource.create()
            resource.set_tech_id(tech_id)
            print(f"[DEPLOY] ✓ Created: {resource_id} → {tech_id}")
        self.new_deployed_state[resource_id] = resource
        self.new_iac_mapping.resources[resource_id] = ResourceMapping(
            type=resource_type,
            tech_id=resource.get_tech_id()
        )
        self.deployment_progress.total_deployed += 1
        self.deployment_progress.deployed_resource_ids.append(resource_id)

        # Save intermediate state for recovery
        self._save_intermediate_config()

    def _save_intermediate_config(self) -> None:
        """Save intermediate deployment state for recovery"""
        from dataclasses import asdict
        config_with_progress = IacMapping(
            resources=self.new_iac_mapping.resources,
            deployment_progress=asdict(self.deployment_progress)
        )
        config_with_progress.to_yaml(self.config_file)

    def __enter__(self) -> "TransactionalDeploymentContext":
        """Enter context manager"""
        print(f"[DEPLOY] Starting deployment for app: {self.app.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager and handle cleanup"""
        if exc_type is not None:
            # Deployment failed - save partial state for recovery
            print(f"[ERROR] Deployment failed: {exc_val}")
            print(f"[RECOVERY] Saved partial state: {self.deployment_progress.total_deployed} resources deployed")
            self.deployment_failed = True
            # Config with progress is already saved via _save_intermediate_config()
            return False  # Re-raise the exception

        # Deployment succeeded - cleanup old resources
        print(f"[DEPLOY] All resources deployed successfully ({self.deployment_progress.total_deployed}/{len(self.app.constructs)})")
        self._cleanup_old_resources()
        self._finalize_config()
        return False

    def _cleanup_old_resources(self) -> None:
        """Delete resources that are no longer in desired state (in reverse order)"""
        to_delete = {}
        for resource_id, resource in self.app.current_state.items():
            if resource_id not in self.new_deployed_state:
                to_delete[resource_id] = resource

        if not to_delete:
            print("[CLEANUP] No resources to delete")
            return

        # Delete in reverse order of deployment
        print(f"[CLEANUP] Deleting {len(to_delete)} old resources in reverse order...")

        # Build reverse order - first deployed resources that need to be deleted
        reverse_order = [rid for rid in reversed(self.deployment_progress.deployed_resource_ids) if rid in to_delete]
        # Then add remaining resources to delete (that weren't in current deployment)
        reverse_order.extend([rid for rid in to_delete.keys() if rid not in reverse_order])

        for resource_id in reverse_order:
            resource = to_delete[resource_id]
            tech_id = self.app.current_config.resources[resource_id].tech_id
            resource_class_name = resource.__class__.__name__
            print(f"[CLEANUP] Deleting: {resource_id} ({resource_class_name})")
            resource.delete(tech_id)
            print(f"[CLEANUP] ✓ Deleted: {resource_id}")

    def _finalize_config(self) -> None:
        """Save final configuration without deployment progress"""
        final_mapping = IacMapping(resources=self.new_iac_mapping.resources)
        final_mapping.to_yaml(self.config_file)
        print(f"[SUCCESS] Config saved: {self.config_file}")
