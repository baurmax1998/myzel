
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
    def get_resource_id(self) -> str:
        """Gebe eine fachliche resource_id zurück (z.B. bucket_name für S3)"""
        pass

    @abstractmethod
    def create(self) -> str:
        pass

    @abstractmethod
    def update(self, field: str = None, old_value: str = None, new_value: str = None, old_technical_id: str = None):
        pass

    @abstractmethod
    def delete(self, tech_id: str):
        pass
