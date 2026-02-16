from pathlib import Path

from pydantic import ValidationError

from src.model import AwsApp, Resources, IacMapping, ResourceMapping, DiffResult
from src.model.registry import get_resource_class, get_resource_type


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
        resource_class = get_resource_class(resource_type)
        if resource_class:
            resource = resource_class.get(resource_mapping.tech_id, app.env)
            deployed_constructs[resource_id] = resource

    desired_constructs: dict[str, Resources] = app.constructs
    desired_iac_mapping = IacMapping()

    # 1. Nur in desired (neue Ressourcen - CREATE)
    for resource_id, resource in desired_constructs.items():
        if resource_id not in deployed_constructs:
            tech_id = resource.create()
            resource_type = get_resource_type(resource)
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
            resource_type = get_resource_type(deployed)
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


def destroy(app: AwsApp, config_dir: Path = Path("config")) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / f"app_{app.name}.yaml"

    try:
        iac_mapping: IacMapping = IacMapping.from_yaml(config_file)
    except ValidationError as e:
        raise RuntimeError(f"Invalid config {config_file}:\n{e}")

    # Lösche alle Ressourcen aus der Config
    for resource_id in iac_mapping.resources:
        resource_mapping = iac_mapping.resources[resource_id]
        resource_type = resource_mapping.type
        tech_id = resource_mapping.tech_id

        resource_class = get_resource_class(resource_type)
        if resource_class:
            resource = resource_class.get(tech_id, app.env)
            resource.delete(tech_id)

    # Leere die Config
    empty_mapping = IacMapping()
    empty_mapping.to_yaml(config_file)


def diff(app: AwsApp, config_dir: Path = Path("config")) -> "DiffResult":
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / f"app_{app.name}.yaml"

    try:
        iac_mapping: IacMapping = IacMapping.from_yaml(config_file)
    except ValidationError as e:
        raise RuntimeError(f"Invalid config {config_file}:\n{e}")

    deployed_constructs: dict[str, Resources] = {}
    for resource_id in iac_mapping.resources:
        resource_mapping = iac_mapping.resources[resource_id]
        resource_type = resource_mapping.type
        resource_class = get_resource_class(resource_type)
        if resource_class:
            resource = resource_class.get(resource_mapping.tech_id, app.env)
            deployed_constructs[resource_id] = resource

    desired_constructs: dict[str, Resources] = app.constructs
    result = DiffResult()

    # 1. Nur in desired (neue Ressourcen - CREATE)
    for resource_id, resource in desired_constructs.items():
        if resource_id not in deployed_constructs:
            result.create[resource_id] = resource

    # 2. In beiden (existierende Ressourcen - UPDATE)
    for resource_id, desired in desired_constructs.items():
        if resource_id in deployed_constructs:
            deployed = deployed_constructs[resource_id]
            if desired != deployed:
                result.update[resource_id] = (deployed, desired)

    # 3. Nur in deployed (zu löschende Ressourcen - DELETE)
    for resource_id, resource in deployed_constructs.items():
        if resource_id not in desired_constructs:
            result.delete[resource_id] = resource

    result.print()
    return result
