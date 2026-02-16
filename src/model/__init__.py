from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Type

@dataclass
class AwsEnviroment:
    profile: str = "bins-example-dev"
    account: str = "967243681795"
    region: str = "eu-central-1"



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