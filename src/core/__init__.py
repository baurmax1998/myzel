from pathlib import Path
from typing import Dict
import yaml
from pydantic import BaseModel, Field, ValidationError


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


def deploy(app, config_dir: Path = Path("config")) -> IacMapping:
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / f"app_{app.name}.yaml"

    try:
        iac = IacMapping.from_yaml(config_file)
    except ValidationError as e:
        raise RuntimeError(f"Invalid config {config_file}:\n{e}")

    # hier deine Deploy-Logik …
    # z.B. iac.resources["db"] = ResourceMapping(type="postgres", tech_id="rds-123")

    iac.to_yaml(config_file)
    return iac
