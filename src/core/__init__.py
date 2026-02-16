from pathlib import Path
from typing import Dict
import yaml
from pydantic import BaseModel, Field, ValidationError

from src.model import AwsApp
from src.resources import Resources
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



    iac_mapping.to_yaml(config_file)
    return iac_mapping
