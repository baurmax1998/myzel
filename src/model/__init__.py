from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, Type, Dict

import yaml
from pydantic import BaseModel, Field


@dataclass
class AwsEnviroment:
    profile: str
    account: str
    region: str



T = TypeVar('T', bound='Resources')


class Resources(ABC):  # Interface

    @classmethod
    @abstractmethod
    def list(cls: Type[T], env: AwsEnviroment) -> list[T]:
        pass

    @classmethod
    @abstractmethod
    def get(cls: Type[T], tech_id: str, env: AwsEnviroment) -> T:
        pass

    @abstractmethod
    def create(self) -> str:
        pass

    @abstractmethod
    def update(self, deployed_tech_id: str, new_value: T) -> str:
        pass

    @abstractmethod
    def delete(self, tech_id: str):
        pass

@dataclass
class AwsApp:
    name: str
    env: AwsEnviroment
    constructs: dict[str, Resources]



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