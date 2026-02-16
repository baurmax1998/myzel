from pathlib import Path
from typing import Dict
import yaml
from pydantic import BaseModel, Field, ValidationError

from src.model import AwsApp, Resources
from src.resources.s3 import S3


class ResourceMapping(BaseModel):
    type: str = Field(..., min_length=1)
    tech_id: str = Field(..., min_length=1)


class IacMapping(BaseModel):
    resources: Dict[str, ResourceMapping] = Field(default_factory=dict)

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


def deploy(app: AwsApp, config_dir: Path = Path("config")) -> IacMapping:
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / f"app_{app.name}.yaml"

    try:
        iac_mapping:IacMapping = IacMapping.from_yaml(config_file)
    except ValidationError as e:
        raise RuntimeError(f"Invalid config {config_file}:\n{e}")

    deployed_constructs: dict[str, Resources] = {}
    for resource_id in iac_mapping.resources:
        resource_mapping = iac_mapping.resources[resource_id]
        resource_type = resource_mapping.type
        if resource_type == "s3":
            resource = S3.get(resource_mapping.tech_id, app.env)
            deployed_constructs[resource_id] = resource

    desired_constructs: dict[str, Resources] = app.constructs
    desired_iac_mapping = IacMapping()

    # 1. Nur in desired (neue Ressourcen - CREATE)
    for resource_id, resource in desired_constructs.items():
        if resource_id not in deployed_constructs:
            tech_id = resource.create()
            # Bestimme den Ressourcentyp
            resource_type = "s3" if isinstance(resource, S3) else "unknown"
            desired_iac_mapping.resources[resource_id] = ResourceMapping(
                type=resource_type,
                tech_id=tech_id
            )

    # 2. In beiden (existierende Ressourcen - UPDATE)
    for resource_id, desired in desired_constructs.items():
        if resource_id in deployed_constructs:
            deployed = deployed_constructs[resource_id]
            tech_id = iac_mapping.resources[resource_id].tech_id
            if desired != deployed:
                new_id = deployed.update(tech_id, desired)
                tech_id = new_id if new_id is not None else tech_id
            resource_type = "s3" if isinstance(deployed, S3) else "unknown"
            desired_iac_mapping.resources[resource_id] = ResourceMapping(
                type=resource_type,
                tech_id=tech_id
            )


    # 3. Nur in deployed (zu löschende Ressourcen - DELETE)
    for resource_id, resource in deployed_constructs.items():
        if resource_id not in desired_constructs:
            tech_id = iac_mapping.resources[resource_id].tech_id
            resource.delete(tech_id)

    desired_iac_mapping.to_yaml(config_file)
    return iac_mapping
