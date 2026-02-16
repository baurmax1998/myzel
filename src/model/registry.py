from typing import Type, Optional

from src.model import Resources

# Registry für Resource-Typen
_resource_registry: dict[str, Type[Resources]] = {}


def register_resource(resource_type: str):
    """Decorator zum Registrieren von Resource-Implementierungen"""
    def decorator(cls: Type[Resources]) -> Type[Resources]:
        _resource_registry[resource_type] = cls
        return cls
    return decorator


def get_resource_type(resource: Resources) -> str:
    """Bestimme den Ressourcentyp basierend auf der Klasse"""
    for resource_type, resource_class in _resource_registry.items():
        if isinstance(resource, resource_class):
            return resource_type
    return "unknown"


def get_resource_class(resource_type: str) -> Optional[Type[Resources]]:
    """Hole die Resource-Klasse für einen Typ"""
    return _resource_registry.get(resource_type)
