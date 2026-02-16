import boto3

from src.resources import Resources
from src.model import AwsEnviroment


class S3(Resources):
    """S3 Resource für AWS Bucket Management"""

    def __init__(
        self,
        bucket_name: str,
        env: AwsEnviroment
    ):
        self.bucket_name = bucket_name
        self.env = env
        self.aws_id = None
        self.s3_client = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        ).client('s3')

    @classmethod
    def list(cls, env: AwsEnviroment) -> list['S3']:
        """Liste alle S3 Buckets auf"""
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        s3_client = session.client('s3')

        try:
            response = s3_client.list_buckets()
            buckets = []
            for bucket in response.get('Buckets', []):
                bucket_name = bucket['Name']
                buckets.append(cls(bucket_name=bucket_name, env=env))
            return buckets
        except Exception as e:
            print(f"Fehler beim Auflisten der Buckets: {e}")
            return []

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'S3':
        """Hole einen spezifischen S3 Bucket anhand des Namens"""
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        s3_client = session.client('s3')

        try:
            # Prüfe ob Bucket existiert
            s3_client.head_bucket(Bucket=tech_id)

            return cls(
                bucket_name=tech_id,
                env=env,
            )
        except Exception as e:
            print(f"Fehler beim Abrufen des Buckets {tech_id}: {e}")
            raise

    def read(self) -> dict:
        """Lese den aktuellen State des S3 Buckets von AWS"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            # Bucket existiert, gebe Properties zurück
            return {
                "bucket_name": self.bucket_name
            }
        except Exception:
            # Bucket existiert nicht
            return None

    def create(self) -> str:
        """Erstelle einen neuen S3 Bucket und gebe die ARN zurück"""
        try:
            kwargs = {
                'Bucket': self.bucket_name,
                'ACL': 'private'
            }

            if self.env.region != 'us-east-1':
                kwargs['CreateBucketConfiguration'] = {
                    'LocationConstraint': self.env.region
                }

            self.s3_client.create_bucket(**kwargs)

            arn = f"arn:aws:s3:::{self.bucket_name}"
            self.aws_id = arn
            print(f"S3 Bucket '{self.bucket_name}' erfolgreich erstellt")
            return arn
        except Exception as e:
            print(f"Fehler beim Erstellen des Buckets: {e}")
            raise

    def update(self, field: str = None, old_value: str = None, new_value: str = None, old_technical_id: str = None):
        """Update die S3 Bucket Konfiguration"""
        try:
            if field == "bucket_name":
                # Für bucket_name: alter Bucket muss gelöscht und neuer erstellt werden
                # (S3 Buckets können nicht umbenannt werden)
                print(f"S3 Bucket wird umbenannt: {old_value} -> {new_value}")

                # 1. Lösche den alten Bucket (nutze old_technical_id aus YAML)
                bucket_to_delete = old_technical_id or old_value
                if bucket_to_delete:
                    try:
                        self.s3_client.delete_bucket(Bucket=bucket_to_delete)
                        print(f"  ✓ Alter Bucket '{bucket_to_delete}' gelöscht")
                    except Exception as e:
                        print(f"  ⚠ Konnte alten Bucket '{bucket_to_delete}' nicht löschen: {e}")

                # 2. Erstelle neuen Bucket
                self.bucket_name = new_value
                kwargs = {
                    'Bucket': self.bucket_name,
                    'ACL': 'private'
                }
                if self.env.region != 'us-east-1':
                    kwargs['CreateBucketConfiguration'] = {
                        'LocationConstraint': self.env.region
                    }
                self.s3_client.create_bucket(**kwargs)
                self.aws_id = f"arn:aws:s3:::{self.bucket_name}"
                print(f"  ✓ Neuer Bucket '{new_value}' erstellt")
            else:
                print(f"S3 Bucket '{self.bucket_name}' wird aktualisiert: {field}={new_value}")
        except Exception as e:
            print(f"Fehler beim Update des Buckets: {e}")
            raise

    def delete(self, tech_id: str = None):
        """Lösche den S3 Bucket und alle Objekte darin"""
        try:
            # Lösche alle Objekte im Bucket
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)

            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        self.s3_client.delete_object(
                            Bucket=self.bucket_name,
                            Key=obj['Key']
                        )

            # Lösche den leeren Bucket
            self.s3_client.delete_bucket(Bucket=self.bucket_name)
            print(f"S3 Bucket '{self.bucket_name}' erfolgreich gelöscht")
        except Exception as e:
            print(f"Fehler beim Löschen des Buckets: {e}")
            raise

    def __repr__(self) -> str:
        return f"S3(bucket='{self.bucket_name}', region='{self.env.region}')"
