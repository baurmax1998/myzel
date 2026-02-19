import os
import boto3
from pathlib import Path

from src.model import AwsEnviroment, Resources
from src.model.registry import register_resource


@register_resource("s3_deploy")
class S3Deploy(Resources):
    """S3 Deployment Resource - Lädt einen lokalen Ordner in einen S3 Bucket hoch"""

    def __init__(
        self,
        bucket_name: str,
        local_path: str,
        s3_path: str,
        env: AwsEnviroment
    ):
        self.bucket_name = bucket_name
        self.local_path = Path(local_path)
        self.s3_path = s3_path.rstrip('/') if s3_path else ''
        self.env = env

    @classmethod
    def list(cls, env: AwsEnviroment) -> list['S3Deploy']:
        """Liste alle S3 Deployments auf"""
        return []

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'S3Deploy':
        """Hole ein spezifisches S3 Deployment"""
        bucket_name, s3_path = cls._extract_from_tech_id(tech_id)
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        s3_client = session.client('s3')

        try:
            s3_client.head_bucket(Bucket=bucket_name)
            return cls(bucket_name=bucket_name, local_path="", s3_path=s3_path, env=env)
        except Exception as e:
            print(f"Fehler beim Abrufen des Deployments: {e}")
            raise

    def create(self) -> str:
        """Erstelle Bucket und lade Dateien hoch"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        s3_client = session.client('s3')

        try:
            # Erstelle Bucket falls nicht vorhanden
            if not self._bucket_exists(self.bucket_name, s3_client):
                print(f"Erstelle S3 Bucket '{self.bucket_name}'")
                if self.env.region == 'us-east-1':
                    s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.env.region}
                    )
            else:
                print(f"S3 Bucket '{self.bucket_name}' existiert bereits")

            # Lade Dateien hoch
            self._upload_directory(s3_client)

            tech_id = self._create_tech_id(self.bucket_name, self.s3_path)
            print(f"Dateien erfolgreich in S3 Bucket '{self.bucket_name}/{self.s3_path}' hochgeladen")
            return tech_id

        except Exception as e:
            print(f"Fehler beim S3 Deployment: {e}")
            raise

    def update(self, deployed_tech_id: str, new_value: 'S3Deploy') -> str:
        """Update Deployment - lade neue Dateien hoch"""
        session = boto3.session.Session(
            profile_name=new_value.env.profile,
            region_name=new_value.env.region
        )
        s3_client = session.client('s3')

        try:
            deployed_bucket, deployed_path = self._extract_from_tech_id(deployed_tech_id)

            # Wenn Bucket oder Pfad sich ändern, leere den alten Pfad
            if deployed_bucket == new_value.bucket_name and deployed_path == new_value.s3_path:
                print(f"Update S3 Deployment in Bucket '{new_value.bucket_name}/{new_value.s3_path}'")
                new_value._clear_prefix(s3_client, new_value.s3_path)
            else:
                print(f"Ändere S3 Deployment von '{deployed_bucket}/{deployed_path}' zu '{new_value.bucket_name}/{new_value.s3_path}'")
                new_value._clear_prefix(s3_client, deployed_path)

            # Lade neue Dateien hoch
            new_value._upload_directory(s3_client)

            tech_id = new_value._create_tech_id(new_value.bucket_name, new_value.s3_path)
            print(f"S3 Deployment erfolgreich aktualisiert")
            return tech_id

        except Exception as e:
            print(f"Fehler beim Update des Deployments: {e}")
            raise

    def delete(self, tech_id: str):
        """Lösche alle Dateien aus dem S3 Pfad"""
        bucket_name, s3_path = self._extract_from_tech_id(tech_id)
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        s3_client = session.client('s3')

        try:
            print(f"Lösche Inhalte aus S3 Bucket '{bucket_name}/{s3_path}'")
            self._clear_prefix(s3_client, s3_path)
            print(f"Inhalte erfolgreich gelöscht")
        except Exception as e:
            print(f"Fehler beim Löschen: {e}")
            raise

    def _bucket_exists(self, bucket_name: str, s3_client) -> bool:
        """Prüfe ob ein Bucket existiert"""
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            return True
        except:
            return False

    def _upload_directory(self, s3_client):
        """Lade alle Dateien aus local_path in S3 hoch"""
        if not self.local_path.exists():
            raise FileNotFoundError(f"Pfad existiert nicht: {self.local_path}")

        if not self.local_path.is_dir():
            raise NotADirectoryError(f"Pfad ist kein Verzeichnis: {self.local_path}")

        for file_path in self.local_path.rglob('*'):
            if file_path.is_file():
                # Berechne relativen Pfad für S3 Key
                relative_path = file_path.relative_to(self.local_path)
                s3_key = str(relative_path).replace('\\', '/')  # Windows Kompatibilität

                # Prepend s3_path wenn vorhanden
                if self.s3_path:
                    s3_key = f"{self.s3_path}/{s3_key}"

                print(f"  Lade hoch: {s3_key}")
                s3_client.upload_file(
                    Filename=str(file_path),
                    Bucket=self.bucket_name,
                    Key=s3_key
                )

    def _clear_prefix(self, s3_client, prefix: str):
        """Lösche alle Objekte mit einem bestimmten Präfix"""
        if not prefix:
            return

        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    print(f"  Lösche: {obj['Key']}")
                    s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])

    def _clear_bucket(self, s3_client):
        """Lösche alle Objekte aus dem Bucket"""
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket_name)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    print(f"  Lösche: {obj['Key']}")
                    s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])

    @staticmethod
    def _create_tech_id(bucket_name: str, s3_path: str) -> str:
        """Erstelle tech_id aus Bucket-Name und S3-Pfad"""
        if s3_path:
            return f"s3://{bucket_name}/{s3_path}"
        return f"s3://{bucket_name}"

    @staticmethod
    def _extract_from_tech_id(tech_id: str) -> tuple:
        """Extrahiere Bucket-Name und S3-Pfad aus tech_id"""
        # Format: s3://bucket-name oder s3://bucket-name/path
        if not tech_id.startswith('s3://'):
            raise ValueError(f"Ungültiges tech_id Format: {tech_id}")

        tech_id = tech_id[5:]  # Entferne 's3://'
        parts = tech_id.split('/', 1)
        bucket_name = parts[0]
        s3_path = parts[1] if len(parts) > 1 else ''

        return bucket_name, s3_path

    def __repr__(self) -> str:
        return f"S3Deploy(bucket='{self.bucket_name}', s3_path='{self.s3_path}', local_path='{self.local_path}')"
