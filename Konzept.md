# AWS IAC Konzept - Infrastructure as Code mit Diff-Management

## Überblick

Ein Custom IAC-Framework in Python, das AWS-Ressourcen über Klassen repräsentiert, den aktuellen Zustand in einer YAML-Config speichert und Diffs automatisch erkennt und auflöst.

---

## 1. Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────┐
│                   AWS IAC Application                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Resource Klassen (abstrakt)               │   │
│  │  - BaseResource (CRUD-Schnittstelle)             │   │
│  │  - EC2Instance, S3Bucket (konkrete Impl.)        │   │
│  └──────────────────────────────────────────────────┘   │
│                          △                               │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │      State Manager (Config Persistierung)        │   │
│  │  - YAML Config lesen/schreiben                   │   │
│  │  - aktuellen State tracken                       │   │
│  └──────────────────────────────────────────────────┘   │
│                          △                               │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │        Diff Engine (Vergleich & Auflösung)      │   │
│  │  - desired vs. actual State vergleichen          │   │
│  │  - Diffs identifizieren (C/U/D)                  │   │
│  │  - Dry-Run oder Apply                           │   │
│  └──────────────────────────────────────────────────┘   │
│                          △                               │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Main Application (CLI/API)             │   │
│  │  - user interactions                             │   │
│  │  - orchestration                                 │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Resource Klassen Design

### 2.1 BaseResource (abstrakte Basisklasse)

```python
class BaseResource(ABC):
    """Abstrakte Basisklasse für alle AWS-Ressourcen"""

    # Eigenschaften
    - resource_type: str          # z.B. "EC2Instance", "S3Bucket"
    - resource_id: str            # eindeutige ID
    - properties: dict            # Konfigurationsparameter
    - aws_id: str | None          # AWS-spezifische ID
    - tags: dict                  # AWS Tags
    - state: ResourceState        # aktueller State (PENDING, ACTIVE, DELETED)

    # Abstrakte CRUD-Methoden
    def create() -> bool          # Create in AWS
    def read() -> dict | None     # liest aktuellen State von AWS
    def update(changes: dict)     # Update durchführen
    def delete() -> bool          # Ressource löschen

    # Hilfsmethoden
    def to_dict() -> dict         # Serialisierung für Config
    def from_dict(data: dict)     # Deserialisierung
    def get_diff(desired: dict) -> Diff  # vergleicht mit desired State
```

### 2.2 Konkrete Resource-Implementierungen

#### EC2Instance
```python
class EC2Instance(BaseResource):
    def __init__(self, resource_id, instance_type, ami_id, **kwargs):
        self.resource_type = "EC2Instance"
        self.instance_type = instance_type
        self.ami_id = ami_id
        # ...

    def create() -> bool:
        # boto3 client.run_instances() aufrufen
        # aws_id speichern

    def read() -> dict | None:
        # boto3 client.describe_instances() aufrufen
        # aktuellen State zurückgeben

    def update(changes: dict):
        # je nach Property unterschiedliche Update-Strategien
        # z.B. instance stop/modify/start für manche Properties

    def delete() -> bool:
        # boto3 client.terminate_instances() aufrufen
```

#### S3Bucket
```python
class S3Bucket(BaseResource):
    def __init__(self, resource_id, region, **kwargs):
        self.resource_type = "S3Bucket"
        self.region = region
        # ...

    # ähnliche CRUD-Implementierung für S3
```

---

## 3. State Management & Konfiguration

### 3.1 State Manager Klasse

```python
class StateManager:
    """Verwaltet Persistierung und Abruf des aktuellen IAC-States"""

    def __init__(self, config_file_path: str):
        self.config_path = config_file_path  # z.B. "iac-state.yaml"

    def load_state() -> dict:
        """YAML-Config laden"""
        # liest iac-state.yaml
        # gibt dict mit allen Ressourcen zurück

    def save_state(state: dict) -> None:
        """State in YAML speichern"""
        # serialisiert dict zu YAML

    def update_resource(resource_id: str, data: dict) -> None:
        """einzelne Ressource updaten"""

    def delete_resource(resource_id: str) -> None:
        """Ressource aus Config entfernen"""

    def get_resource(resource_id: str) -> dict | None:
        """einzelne Ressource abrufen"""
```

### 3.2 YAML Config Format

```yaml
# iac-state.yaml
resources:
  ec2_web_server:
    resource_type: EC2Instance
    resource_id: ec2_web_server
    aws_id: i-1234567890abcdef0  # wird von AWS zurückgegeben
    state: ACTIVE
    properties:
      instance_type: t3.micro
      ami_id: ami-0c55b159cbfafe1f0
      subnet_id: subnet-12345
      security_groups:
        - sg-12345
    tags:
      Environment: production
      Name: WebServer
    created_at: 2024-02-14T10:00:00Z
    last_modified: 2024-02-14T10:05:00Z

  s3_app_bucket:
    resource_type: S3Bucket
    resource_id: s3_app_bucket
    aws_id: my-app-bucket-12345
    state: ACTIVE
    properties:
      bucket_name: my-app-bucket-12345
      region: eu-central-1
      versioning: enabled
      encryption:
        type: AES256
    tags:
      Environment: production
    created_at: 2024-02-14T09:00:00Z
    last_modified: 2024-02-14T09:00:00Z

metadata:
  version: "1.0"
  last_sync: 2024-02-14T10:05:00Z
  created_by: admin
```

---

## 4. Diff Engine

### 4.1 Diff-Klasse und -Typen

```python
class Diff:
    """Repräsentiert eine Änderung"""

    resource_id: str
    resource_type: str
    diff_type: DiffType  # CREATE, UPDATE, DELETE
    field: str           # welche Property betroffen
    current_value: Any   # aktueller Wert (AWS)
    desired_value: Any   # gewünschter Wert (Config)

class DiffType(Enum):
    CREATE = "CREATE"    # Ressource existiert in Config, nicht in AWS
    UPDATE = "UPDATE"    # Property unterscheidet sich
    DELETE = "DELETE"    # Ressource existiert in AWS, nicht in Config
```

### 4.2 DiffEngine Klasse

```python
class DiffEngine:
    """Vergleicht desired State mit actual State"""

    def __init__(self, state_manager: StateManager, resources: dict):
        self.state_manager = state_manager
        self.resources = resources  # aktive Resource-Objekte

    def calculate_diffs() -> list[Diff]:
        """Vergleicht Config mit AWS"""
        diffs = []

        # 1. Iterate über alle Ressourcen in Config
        for resource_id, config_data in state_manager.load_state()["resources"].items():
            resource = self.resources[resource_id]

            # 2. Aktuellen AWS-State abrufen
            actual_state = resource.read()

            # 3. Vergleichen
            if actual_state is None:
                # Ressource in Config, aber nicht in AWS -> CREATE
                diffs.append(Diff(resource_id, resource.resource_type, DiffType.CREATE, ...))
            else:
                # Eigenschaften vergleichen
                for prop, desired_val in config_data["properties"].items():
                    actual_val = actual_state.get(prop)
                    if actual_val != desired_val:
                        diffs.append(Diff(resource_id, ..., DiffType.UPDATE, prop, actual_val, desired_val))

        # 4. Ressourcen in AWS, aber nicht in Config -> DELETE
        # (kann durch Tracking ermittelt werden)

        return diffs

    def apply_diffs(diffs: list[Diff], dry_run: bool = True) -> ApplyResult:
        """Wendet Diffs an"""
        results = []

        for diff in diffs:
            resource = self.resources[diff.resource_id]

            try:
                if dry_run:
                    # Nur anzeigen, nicht durchführen
                    results.append(ApplyResult(diff, status="DRY_RUN", message=f"Would {diff.diff_type}..."))
                else:
                    if diff.diff_type == DiffType.CREATE:
                        resource.create()
                    elif diff.diff_type == DiffType.UPDATE:
                        resource.update({diff.field: diff.desired_value})
                    elif diff.diff_type == DiffType.DELETE:
                        resource.delete()

                    results.append(ApplyResult(diff, status="SUCCESS"))

            except Exception as e:
                results.append(ApplyResult(diff, status="FAILED", error=str(e)))

        return ApplyResult(results)
```

---

## 5. Workflow & Anwendungsszenarien

### 5.1 Typical Workflows

#### Szenario 1: Neue Ressourcen hinzufügen
```
1. Developer schreibt neue Ressource in Code
2. resource = EC2Instance("web_server", instance_type="t3.micro", ...)
3. state_manager.save_resource(resource)
4. cli.plan()  → zeigt CREATE Diff
5. cli.apply(dry_run=True)  → zeigt was passiert
6. cli.apply(dry_run=False)  → erstellt in AWS, speichert aws_id
```

#### Szenario 2: Ressource modifizieren
```
1. Config wird geändert (z.B. security_groups)
2. diff_engine.calculate_diffs()  → findet UPDATE
3. cli.plan()  → zeigt UPDATE Diff
4. cli.apply(dry_run=True)
5. cli.apply(dry_run=False)  → wendet Change an
```

#### Szenario 3: AWS-Drift erkennen
```
1. Jemand ändert EC2-Instance manuell in AWS Console
2. cli.refresh()  → ruft aktuelle States ab
3. diff_engine.calculate_diffs()  → erkennt Unterschied
4. cli.show_diffs()  → zeigt Drift
5. User kann sich entscheiden:
   - Config anpassen (accept AWS state)
   - apply(dry_run=False)  → stellt Config wieder her
```

---

## 6. Implementierungs-Phasen

### Phase 1: Grundgerüst
- [ ] BaseResource abstrakte Klasse
- [ ] StateManager mit YAML I/O
- [ ] EC2Instance & S3Bucket Implementierungen
- [ ] CLI-Grundgerüst

### Phase 2: Diff Engine
- [ ] Diff-Klasse und DiffType Enum
- [ ] DiffEngine.calculate_diffs()
- [ ] DiffEngine.apply_diffs() mit dry_run
- [ ] Diff-Visualisierung im CLI

### Phase 3: AWS Integration
- [ ] boto3 Integration für EC2
- [ ] boto3 Integration für S3
- [ ] Error Handling & Retry-Logik
- [ ] AWS Credentials Management

### Phase 4: Erweiterte Features
- [ ] weitere Ressourcentypen hinzufügen
- [ ] Resource Dependencies (z.B. Security Group → EC2)
- [ ] Rollback-Funktionalität
- [ ] State Locking (für Multi-User)
- [ ] Audit-Log

---

## 7. Projektstruktur

```
myzel/
├── Konzept.md                          # dieses Dokument
├── pyproject.toml
├── requirements.txt
├── iac_framework/
│   ├── __init__.py
│   ├── core/
│   │   ├── base_resource.py           # BaseResource abstrakte Klasse
│   │   ├── state_manager.py           # StateManager für YAML
│   │   └── diff_engine.py             # DiffEngine Logik
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── ec2_instance.py            # EC2Instance Klasse
│   │   └── s3_bucket.py               # S3Bucket Klasse
│   ├── aws/
│   │   ├── __init__.py
│   │   ├── ec2_client.py              # boto3 EC2 wrapper
│   │   └── s3_client.py               # boto3 S3 wrapper
│   └── cli.py                          # CLI-Interface
├── config/
│   └── iac-state.yaml                 # aktueller State
├── tests/
│   ├── test_resources.py
│   ├── test_state_manager.py
│   └── test_diff_engine.py
└── README.md
```

---

## 8. Technische Entscheidungen

| Aspekt | Entscheidung | Begründung |
|--------|-------------|-----------|
| Sprache | Python | Gute AWS boto3 Integration, schnelle Entwicklung |
| Config Format | YAML | Lesbar, gut für IaC üblich |
| State Persistierung | Local YAML | Einfach zum Starten, später Git/Remote möglich |
| Dry-Run | immer möglich | Safety First - User sieht was passiert |
| Error Handling | Exception-basiert | Python Standard |
| Testing | pytest | Standard für Python |

---

## 9. Zukünftige Erweiterungen

- [ ] Remote State (S3, DynamoDB)
- [ ] State Locking für Team-Arbeit
- [ ] Resource Templating (Jinja2)
- [ ] mehr AWS Services (RDS, Lambda, VPC, etc.)
- [ ] CloudFormation/Terraform Import
- [ ] Monitoring & Drift Detection Automation
- [ ] Web UI für State-Management

---

## 10. Design Patterns

| Pattern | Anwendung |
|---------|-----------|
| **Strategy** | verschiedene Diff-Auflösungs-Strategien |
| **Factory** | Resource-Klassen basierend auf resource_type erstellen |
| **Observer** | State-Changes tracken |
| **Command** | CLI-Commands als Command-Objekte |

---

## Nächste Schritte

1. Feedback zum Konzept geben
2. Phase 1 implementieren
3. mit einfacher CLI testen
4. iterativ erweitern