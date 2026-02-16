from pathlib import Path

from pydantic import ValidationError

from src.model import AwsApp, IacMapping
from src.model.registry import get_resource_class


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
