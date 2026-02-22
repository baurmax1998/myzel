import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import boto3

from src.model import AwsEnviroment, Resources
from src.model.registry import register_resource


@register_resource("lambda")
class LambdaFunction(Resources):
    """Lambda Function Resource für AWS Lambda Management"""

    def __init__(
        self,
        function_name: str,
        handler: str,
        runtime: str,
        code_path: str,
        role_arn: str,
        env: AwsEnviroment,
        environment_variables: dict = None,
        timeout: int = 30,
        memory_size: int = 128
    ):
        self.function_name = function_name
        self.handler = handler
        self.runtime = runtime
        self.code_path = Path(code_path)
        self.role_arn = role_arn
        self.env = env
        self.environment_variables = environment_variables or {}
        self.timeout = timeout
        self.memory_size = memory_size

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'LambdaFunction':
        """Hole eine spezifische Lambda Function"""
        function_name = cls._extract_function_name(tech_id)
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        lambda_client = session.client('lambda')

        try:
            response = lambda_client.get_function(FunctionName=function_name)
            config = response['Configuration']

            return cls(
                function_name=config['FunctionName'],
                handler=config['Handler'],
                runtime=config['Runtime'],
                code_path="",
                role_arn=config['Role'],
                env=env,
                environment_variables=config.get('Environment', {}).get('Variables', {}),
                timeout=config['Timeout'],
                memory_size=config['MemorySize']
            )
        except Exception as e:
            print(f"Fehler beim Abrufen der Lambda Function {function_name}: {e}")
            raise

    def create(self) -> str:
        """Erstelle eine neue Lambda Function oder verwende existierende"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        lambda_client = session.client('lambda')
        iam_client = session.client('iam')

        try:
            existing_function = lambda_client.get_function(FunctionName=self.function_name)
            print(f"Lambda Function existiert bereits: {self.function_name}")
            arn = existing_function['Configuration']['FunctionArn']

            return self.update(arn, self)

        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"Warte auf IAM Role Propagation...")
            self._wait_for_role_propagation(iam_client)

            zip_file = self._create_deployment_package()

            try:
                with open(zip_file, 'rb') as f:
                    zip_content = f.read()

                function_config = {
                    'FunctionName': self.function_name,
                    'Runtime': self.runtime,
                    'Role': self.role_arn,
                    'Handler': self.handler,
                    'Code': {'ZipFile': zip_content},
                    'Timeout': self.timeout,
                    'MemorySize': self.memory_size
                }

                if self.environment_variables:
                    function_config['Environment'] = {
                        'Variables': self.environment_variables
                    }

                response = lambda_client.create_function(**function_config)

                arn = response['FunctionArn']
                print(f"Lambda Function erstellt: {self.function_name}")
                print(f"ARN: {arn}")
                print(f"Runtime: {self.runtime}")
                print(f"Handler: {self.handler}")

                return arn

            finally:
                if os.path.exists(zip_file):
                    os.remove(zip_file)

    def update(self, deployed_tech_id: str, new_value: 'LambdaFunction') -> str:
        """Update eine Lambda Function"""
        function_name = self._extract_function_name(deployed_tech_id)

        session = boto3.session.Session(
            profile_name=new_value.env.profile,
            region_name=new_value.env.region
        )
        lambda_client = session.client('lambda')

        zip_file = new_value._create_deployment_package()

        try:
            with open(zip_file, 'rb') as f:
                zip_content = f.read()

            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print(f"Lambda Code aktualisiert: {function_name}")

            print(f"Warte auf Code Update Abschluss...")
            new_value._wait_for_function_update(lambda_client, function_name)

            config_updates = {
                'FunctionName': function_name,
                'Runtime': new_value.runtime,
                'Role': new_value.role_arn,
                'Handler': new_value.handler,
                'Timeout': new_value.timeout,
                'MemorySize': new_value.memory_size
            }

            if new_value.environment_variables:
                config_updates['Environment'] = {
                    'Variables': new_value.environment_variables
                }

            response = lambda_client.update_function_configuration(**config_updates)

            arn = response['FunctionArn']
            print(f"Lambda Configuration aktualisiert: {function_name}")

            return arn

        finally:
            if os.path.exists(zip_file):
                os.remove(zip_file)

    def delete(self, tech_id: str):
        """Lösche eine Lambda Function"""
        function_name = self._extract_function_name(tech_id)

        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        lambda_client = session.client('lambda')

        try:
            lambda_client.delete_function(FunctionName=function_name)
            print(f"Lambda Function gelöscht: {function_name}")
        except Exception as e:
            print(f"Fehler beim Löschen der Lambda Function: {e}")
            raise

    def _create_deployment_package(self) -> str:
        """Erstelle ZIP Deployment Package"""
        if not self.code_path.exists():
            raise FileNotFoundError(f"Code Pfad existiert nicht: {self.code_path}")

        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f"{self.function_name}.zip")

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if self.code_path.is_file():
                    zipf.write(self.code_path, arcname=self.code_path.name)
                else:
                    for file_path in self.code_path.rglob('*'):
                        if file_path.is_file():
                            if any(part.startswith('.') for part in file_path.parts):
                                continue
                            if '__pycache__' in file_path.parts:
                                continue
                            if file_path.suffix in ['.pyc', '.pyo']:
                                continue
                            if file_path.name in ['test_lambda.py', 'README.md', 'pyproject.toml', '.python-version']:
                                continue

                            arcname = file_path.relative_to(self.code_path)
                            zipf.write(file_path, arcname=arcname)
                            print(f"  Packe: {arcname}")

            print(f"Deployment Package erstellt: {zip_path}")
            return zip_path

        except Exception as e:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e

    def _wait_for_role_propagation(self, iam_client):
        """Warte bis IAM Role verfügbar ist"""
        import time
        role_name = self.role_arn.split('/')[-1]

        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                iam_client.get_role(RoleName=role_name)
                time.sleep(2)
                print(f"IAM Role verfügbar")
                return
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"  Warte auf Role... (Versuch {attempt + 1}/{max_attempts})")
                    time.sleep(2)
                else:
                    raise

    def _wait_for_function_update(self, lambda_client, function_name):
        """Warte bis Lambda Function Update abgeschlossen ist"""
        import time

        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = lambda_client.get_function(FunctionName=function_name)
                state = response['Configuration']['State']
                last_update_status = response['Configuration']['LastUpdateStatus']

                if state == 'Active' and last_update_status == 'Successful':
                    print(f"Lambda Function Update abgeschlossen")
                    return

                if last_update_status == 'Failed':
                    raise Exception(f"Lambda Update fehlgeschlagen")

                print(f"  Warte auf Update... (State: {state}, Status: {last_update_status})")
                time.sleep(2)

            except Exception as e:
                if 'Update' in str(e) or 'progress' in str(e):
                    time.sleep(2)
                else:
                    raise

        raise Exception(f"Timeout beim Warten auf Lambda Update nach {max_attempts * 2} Sekunden")

    @staticmethod
    def _extract_function_name(arn: str) -> str:
        """Extrahiere Function Name aus ARN"""
        return arn.split(':')[-1]

    def __repr__(self) -> str:
        return f"LambdaFunction(name='{self.function_name}', runtime='{self.runtime}')"
