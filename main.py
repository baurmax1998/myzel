from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic


class S3:
    def __init__(self, id: str, bucket_name: str):
        self.id = id
        self.bucket_name = bucket_name

    def get_state(self) -> dict:
        return {
            "id": self.id,
            "bucket_name": self.bucket_name
        }



class Stack:
    def __init__(self, id: str):
        self.id = id

    def render(self):
        s3 = S3("myBucket", "testmb-652")
        pass








# Definiere einen generischen Typ T
T = TypeVar('T')

# Abstrakte, generische Klasse
class MyAbstractClass(ABC, Generic[T]):
    def __init__(self, value: T):
        self.value: T = value  # Generic Field

    @abstractmethod
    def process(self) -> None:
        """Abstrakte Methode, die den Generic-Typ verwenden kann"""
        pass


class Component(ABC):
    id: str
    parent: "Component"
    state: Any

    @abstractmethod
    def fahren(self):
        pass

    @abstractmethod
    def bremsen(self):
        pass


@dataclass
class Data:
    test: str


