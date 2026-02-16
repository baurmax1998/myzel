from abc import ABC, abstractmethod
from typing import TypeVar, Type

from src.model import AwsEnviroment

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
    def update(self, deployed_tech_id: str = None, new_value: T = None) -> str:
        pass

    @abstractmethod
    def delete(self, tech_id: str):
        pass
