from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TypeVar, Type, Dict, Optional

import yaml
from pydantic import BaseModel, Field


@dataclass
class AwsEnviroment:
    profile: str
    account: str
    region: str



T = TypeVar('T', bound='Resources')


class Resources(ABC):
    """
    Abstract base class for all AWS resources in Myzel.

    Defines the lifecycle interface for Infrastructure as Code resources:
    - get: Fetch resource state from AWS
    - create: Create or ensure resource exists in AWS
    - update: Update resource to desired state
    - delete: Remove resource from AWS

    All implementations MUST be idempotent and handle graceful degradation.
    """

    _tech_id: Optional[str] = None

    def get_tech_id(self) -> Optional[str]:
        """Get the technical identifier of this resource instance"""
        return self._tech_id

    def set_tech_id(self, tech_id: str) -> None:
        """Set the technical identifier of this resource instance"""
        self._tech_id = tech_id

    @classmethod
    @abstractmethod
    def get(cls: Type[T], tech_id: str, env: AwsEnviroment) -> T:
        """
        Fetch the current state of a resource from AWS.

        This method retrieves the deployed resource's configuration and state from AWS,
        allowing comparison with the desired state defined in code.

        Args:
            tech_id (str): The technical identifier of the resource (usually ARN or ID).
                          Format varies by resource type (e.g., ARN for Lambda, bucket name for S3).
            env (AwsEnviroment): AWS environment configuration (profile, region, account).

        Returns:
            T: A new instance of the Resource class populated with the current AWS state.

        Behavior:
            - MUST return a valid resource object even if the resource doesn't exist in AWS
            - If resource not found: Return empty/default instance (don't raise exception)
            - If fetching fails for other reasons: Log error and optionally raise
            - This enables graceful handling during destroy operations

        Examples:
            - S3: Returns S3 object with bucket config from AWS
            - Lambda: Returns LambdaFunction with current code, config, env vars
            - DynamoDB: Returns DynamoDB table schema from describe_table
            - Non-existent: Returns empty resource object without error
        """
        pass

    @abstractmethod
    def create(self) -> str:
        """
        Create or ensure the resource exists in AWS with the desired configuration.

        This method is idempotent - calling it multiple times should not fail or create
        duplicate resources. If the resource already exists, verify it matches the
        desired state or update it accordingly.

        Returns:
            str: The technical identifier of the resource (ARN, endpoint URL, etc.)
                This tech_id will be used as input to get() and other methods.

        Behavior:
            - MUST be idempotent: Calling twice should succeed both times
            - If resource exists: Verify/update it, don't create duplicate
            - If resource doesn't exist: Create it with desired configuration
            - Wait for resource to be fully ready (use waiters when available)
            - Return the tech_id that can be used with get(), update(), delete()

        Examples:
            - S3: Create bucket if not exists, apply policy, return ARN
            - Lambda: Create/update function code and config, return ARN
            - DynamoDB: Create table, wait for ACTIVE status, return ARN
            - API Gateway: Create API with routes and integrations, return endpoint

        Raises:
            Exception: Only on actual failures (permissions, invalid config, etc.)
        """
        pass

    @abstractmethod
    def update(self, deployed_tech_id: str, new_value: T) -> str:
        """
        Update a resource to match the desired state (new_value).

        This method transitions the resource from its current deployed state to a new
        desired state. It's called during the deploy phase when changes are detected.

        Args:
            deployed_tech_id (str): The tech_id of the currently deployed resource
            new_value (T): A new instance of the same Resource class with desired config

        Returns:
            str: The tech_id of the (possibly new) resource after update

        Behavior:
            - If deployed resource doesn't exist: Create new one using new_value.create()
            - If deployed resource exists: Update it to match new_value configuration
            - Handle all edge cases gracefully (missing fields, type changes, etc.)
            - Use the same return format as create() for consistency
            - MUST be idempotent: calling update twice with same new_value should be safe

        Examples:
            - S3: If bucket name same → update policy; if different → create new, sync, delete old
            - Lambda: If not exists → create; if exists → update code and config
            - DynamoDB: If not exists → create; if exists → can't modify keys (recreate if needed)
            - API Gateway: If not exists → create new; if exists → update routes

        Note:
            This is where the "fallback to create" logic lives - if the deployed resource
            is gone, we create a new one rather than failing the deployment.
        """
        pass

    @abstractmethod
    def delete(self, tech_id: str):
        """
        Delete the resource from AWS.

        This method removes the resource and all its dependencies from AWS. It must
        handle cases where the resource is already deleted or partially deleted.

        Args:
            tech_id (str): The technical identifier of the resource to delete

        Behavior:
            - MUST be idempotent: Calling twice should succeed both times
            - If resource doesn't exist: Don't raise an error, just return/log
            - If resource has dependencies: Clean them up first (e.g., detach policies)
            - Handle cascade deletions appropriately for resource type
            - Use waiters if resource deletion is asynchronous

        Examples:
            - S3: Empty bucket first (delete all objects), then delete bucket
            - Lambda: Delete function (permissions are auto-cleaned)
            - DynamoDB: Delete table, wait for DELETING → deleted
            - IAM Role: Detach policies first, then delete role
            - API Gateway: Delete routes/integrations first, then API

        Raises:
            Should NOT raise if resource doesn't exist
            Only raise for actual permission/configuration errors

        Note:
            The idempotent behavior is crucial for reliable cleanup in destroy operations.
        """
        pass

@dataclass
class DeploymentProgress:
    """Tracks deployment progress for recovery on failure"""
    total_deployed: int = 0
    deployed_resource_ids: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MyzelApp:
    name: str
    env: AwsEnviroment
    constructs: dict[str, Resources]
    current_config: Optional["IacMapping"] = None
    current_state: dict[str, Resources] = field(default_factory=dict)
    config_dir: Path = field(default_factory=lambda: Path("config"))

    def __post_init__(self):
        """Load existing config and state from AWS"""
        if self.current_config is None:
            self._load_current_state(self.config_dir)

    def _load_current_state(self, config_dir: Path) -> None:
        """Load current config and AWS state"""
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / f"app_{self.name}.yaml"
        self.current_config = IacMapping.from_yaml(config_file)

        # Load current state from AWS
        from src.model.registry import get_resource_class
        for resource_id, resource_mapping in self.current_config.resources.items():
            resource_class = get_resource_class(resource_mapping.type)
            if resource_class:
                resource = resource_class.get(resource_mapping.tech_id, self.env)
                self.current_state[resource_id] = resource

    def begin_deploy(self):
        """Start a transactional deployment"""
        from src.core.transactional_deploy import TransactionalDeploymentContext
        return TransactionalDeploymentContext(self, self.config_dir)



class ResourceMapping(BaseModel):
    type: str = Field(..., min_length=1)
    tech_id: str = Field(..., min_length=1)


class IacMapping(BaseModel):
    resources: Dict[str, ResourceMapping] = Field(default_factory=dict)
    deployment_progress: Optional[Dict] = Field(default=None)

    @classmethod
    def from_yaml(cls, path: Path) -> "IacMapping":
        if not path.exists():
            return cls()

        with path.open() as f:
            data = yaml.safe_load(f) or {}

        return cls.model_validate(data)

    def to_yaml(self, path: Path) -> None:
        with path.open("w") as f:
            yaml.safe_dump(self.model_dump(), f, sort_keys=False)



class DiffResult:
    def __init__(self):
        self.create: dict[str, Resources] = {}
        self.update: dict[str, tuple[Resources, Resources]] = {}
        self.delete: dict[str, Resources] = {}

    def to_yaml_str(self) -> str:
        """Konvertiere DiffResult zu YAML String"""
        data = {
            "create": {resource_id: str(resource) for resource_id, resource in self.create.items()},
            "update": {resource_id: {"old": str(old), "new": str(new)} for resource_id, (old, new) in self.update.items()},
            "delete": {resource_id: str(resource) for resource_id, resource in self.delete.items()}
        }
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def print(self) -> None:
        """Gebe DiffResult als YAML aus"""
        print(self.to_yaml_str())