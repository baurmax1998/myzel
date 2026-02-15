# Deploy-Funktion - Implementierungsguide

## Überblick

Die `deploy()`-Funktion orchestriert die Verwaltung von AWS-Ressourcen mit automatischem Diff-Management. Sie liest die aktuelle Konfiguration, vergleicht sie mit dem AWS-State, führt die Änderungen aus und speichert die neue Version.

## Funktionsweise

### 1. **State-Verwaltung**
Die Funktion speichert den aktuellen State in einer YAML-Datei: `app_<name>_v<version>.yaml`

```yaml
resources:
  '0':
    resource_type: S3Bucket
    resource_id: '0'
    aws_id: arn:aws:s3:::my-bucket
    properties:
      bucket_name: my-bucket
      region: eu-central-1
    created_at: 2026-02-15T10:00:00Z
    last_modified: 2026-02-15T10:00:00Z

metadata:
  version: 1.0.1
  last_sync: 2026-02-15T10:00:00Z
```

### 2. **Diff-Berechnung**
Die DiffEngine vergleicht:
- **CREATE**: Ressource existiert in Config, nicht in AWS
- **UPDATE**: Property unterscheidet sich zwischen Config und AWS
- **DELETE**: Ressource existiert in AWS, nicht in Config

### 3. **Änderungsausführung**
Unterstützt zwei Modi:

#### Dry-Run (Standard)
```python
result = deploy(app, dry_run=True)
# Zeigt nur was passieren würde, ohne Änderungen durchzuführen
```

#### Apply
```python
result = deploy(app, dry_run=False)
# Führt Änderungen aus und speichert neuen State
```

### 4. **Versionsverwaltung**
Nach erfolgreichem Deploy wird die Version automatisch erhöht:
- `1.0` → `1.0.1` → `1.0.2` → ...

## API-Referenz

### `deploy(app, config_dir="config", dry_run=False, auto_increment=True) -> dict`

**Parameter:**
- `app`: AwsApp-Instanz mit `name`, `env`, `constructs`
- `config_dir`: Verzeichnis für YAML-Dateien (Standard: "config")
- `dry_run`: Nur zeigen ohne auszuführen (Standard: False)
- `auto_increment`: Version automatisch erhöhen (Standard: True)

**Rückgabewert:**
```python
{
    "status": "success|partial|failed",
    "diffs_count": int,
    "applied": [{"message": str, "status": str}],
    "failed": [{"error": str}],
    "dry_run": bool,
    "config_file": str
}
```

## Verwendungsbeispiel

```python
from src.core import deploy
from src.examples.example_1 import AwsApp, AwsEnviroment, S3

# Erstelle App
app = AwsApp(
    name="my_app",
    env=AwsEnviroment(profile="my-profile", region="eu-central-1"),
    app_to_tech_id={},
    constructs=[]
)

# Füge Ressourcen hinzu
s3 = S3(bucket_name="my-bucket", env=app.env)
app.constructs.append(s3)

# Dry-Run durchführen
print("Dry-Run:")
result = deploy(app, dry_run=True)

# Wenn alles ok, dann Apply
print("\nApply:")
result = deploy(app, dry_run=False)

# Ergebnis prüfen
if result["status"] == "success":
    print(f"✓ Deploy erfolgreich")
    print(f"  Datei: {result['config_file']}")
```

## Implementierte Module

### `src/core/state_manager.py`
Verwaltet YAML-Persistierung:
- `load_state()`: Liest State aus YAML
- `save_state()`: Speichert State als YAML
- `update_resource()`: Aktualisiert einzelne Ressource
- `delete_resource()`: Entfernt Ressource aus State
- `get_version()`: Liest aktuelle Version

### `src/core/diff_engine.py`
Berechnet und führt Diffs aus:
- `DiffType` Enum: CREATE, UPDATE, DELETE
- `Diff` Dataclass: Repräsentiert einzelne Änderung
- `DiffEngine.calculate_diffs()`: Berechnet alle Diffs
- `DiffEngine.apply_diffs()`: Führt Diffs aus oder zeigt sie im Dry-Run

### `src/core/__init__.py`
Hauptfunktion:
- `deploy()`: Orchestriert den gesamten Deploy-Prozess

## Fehlerbehandlung

Die Funktion behandelt verschiedene Fehlerszenarien:

```python
# Fehlgeschlagene Ressource wird getracked
{
    "status": "partial",
    "failed": [
        {
            "diff": "[CREATE] S3Bucket '0'",
            "error": "Access Denied"
        }
    ]
}

# Kritischer Fehler
{
    "status": "failed",
    "error": "Config file not writable"
}
```

## Workflow-Beispiele

### Szenario 1: Neue Ressourcen hinzufügen
```
1. Ressource zu app.constructs hinzufügen
2. deploy(app, dry_run=True)  → [CREATE] Diff anzeigen
3. deploy(app, dry_run=False) → Ressource erstellen, Version erhöhen
```

### Szenario 2: Ressource konfigurieren
```
1. Ressourceneigenschaften ändern
2. deploy(app, dry_run=True)  → [UPDATE] Diff anzeigen
3. deploy(app, dry_run=False) → Änderung ausführen
```

### Szenario 3: AWS-Drift erkennen
```
1. Jemand ändert Ressource manuell in AWS
2. deploy(app, dry_run=True)  → [UPDATE] Diff zeigt Abweichung
3. Wahl:
   - Config anpassen und deploy
   - deploy(app) durchführen um AWS-State wiederherzustellen
```

## Technische Details

### Versionierung mit `packaging`
```python
from packaging import version

current = "1.0.5"
v = version.parse(current)
new = f"{v.major}.{v.minor}.{v.micro + 1}"  # "1.0.6"
```

### YAML-Speicherung mit PyYAML
```python
import yaml

with open("config.yaml", "w") as f:
    yaml.dump(state, f, default_flow_style=False)
```

## Limitierungen & Zukünftige Erweiterungen

### Aktuelle Limitierungen
- State ist lokal (keine Remote-Locks für Team-Arbeit)
- Keine Rollback-Funktionalität
- Keine Resource-Dependencies
- Keine Dry-Run-Vorschau ohne execute

### Geplante Erweiterungen
- [ ] Remote State (S3, DynamoDB)
- [ ] State Locking für Team-Arbeit
- [ ] Rollback-Funktionalität
- [ ] Resource Dependencies
- [ ] Audit-Log
- [ ] Web UI für State-Management

## Abhängigkeiten

```toml
dependencies = [
    "boto3>=1.26.0",
    "pyyaml>=6.0",
    "packaging>=21.0",
]
```

## Lizenz

MIT
