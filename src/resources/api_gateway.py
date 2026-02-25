import json
import time

import boto3

from src.model import AwsEnviroment, Resources
from src.model.registry import register_resource


@register_resource("api_gateway")
class ApiGateway(Resources):
    """API Gateway Resource für AWS API Gateway Management"""

    def __init__(
        self,
        api_name: str,
        routes: dict,
        env: AwsEnviroment,
        description: str = ""
    ):
        """
        Args:
            api_name: Name des API Gateway
            routes: Dict mit Route Config, z.B.:
                {
                    "/hello": {
                        "method": "GET",
                        "lambda_arn": "arn:aws:lambda:...",
                        "lambda_name": "hallo-welt"
                    }
                }
            env: AWS Environment
            description: API Beschreibung
        """
        self.api_name = api_name
        self.routes = routes
        self.env = env
        self.description = description

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'ApiGateway':
        """Hole ein spezifisches API Gateway"""
        api_id = cls._extract_api_id(tech_id)
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        apigateway_client = session.client('apigatewayv2')

        try:
            response = apigateway_client.get_api(ApiId=api_id)

            return cls(
                api_name=response['Name'],
                routes={},
                env=env,
                description=response.get('Description', '')
            )
        except apigateway_client.exceptions.NotFoundException:
            return cls(
                api_name="",
                routes={},
                env=env
            )
        except Exception as e:
            print(f"Fehler beim Abrufen des API Gateway {api_id}: {e}")
            raise

    def create(self) -> str:
        """Erstelle ein neues API Gateway oder verwende existierendes"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        apigateway_client = session.client('apigatewayv2')
        lambda_client = session.client('lambda')

        try:
            apis = apigateway_client.get_apis()
            existing_api = None
            for api in apis['Items']:
                if api['Name'] == self.api_name:
                    existing_api = api
                    break

            if existing_api:
                print(f"API Gateway existiert bereits: {self.api_name}")
                api_id = existing_api['ApiId']

                # Lösche existierende Routes und Integrationen
                existing_routes = apigateway_client.get_routes(ApiId=api_id)
                for route in existing_routes['Items']:
                    apigateway_client.delete_route(ApiId=api_id, RouteId=route['RouteId'])
                    print(f"  Route gelöscht: {route['RouteKey']}")

                existing_integrations = apigateway_client.get_integrations(ApiId=api_id)
                for integration in existing_integrations['Items']:
                    apigateway_client.delete_integration(ApiId=api_id, IntegrationId=integration['IntegrationId'])
                    print(f"  Integration gelöscht")
            else:
                api_config = {
                    'Name': self.api_name,
                    'ProtocolType': 'HTTP'
                }
                if self.description:
                    api_config['Description'] = self.description

                response = apigateway_client.create_api(**api_config)
                api_id = response['ApiId']
                print(f"API Gateway erstellt: {self.api_name}")
                print(f"API ID: {api_id}")

            self._setup_routes(apigateway_client, lambda_client, api_id)

            stage_name = '$default'
            try:
                apigateway_client.get_stage(ApiId=api_id, StageName=stage_name)
                print(f"Stage existiert bereits: {stage_name}")
            except apigateway_client.exceptions.NotFoundException:
                apigateway_client.create_stage(
                    ApiId=api_id,
                    StageName=stage_name,
                    AutoDeploy=True
                )
                print(f"Stage erstellt: {stage_name}")

            api_endpoint = f"https://{api_id}.execute-api.{self.env.region}.amazonaws.com"
            print(f"API Endpoint: {api_endpoint}")

            return api_endpoint

        except Exception as e:
            print(f"Fehler beim Erstellen des API Gateway: {e}")
            raise

    def _setup_routes(self, apigateway_client, lambda_client, api_id):
        """Setup Routes und Integrationen"""
        for route_path, route_config in self.routes.items():
            method = route_config.get('method', 'GET')
            lambda_arn = route_config['lambda_arn']
            lambda_name = route_config['lambda_name']

            integration_response = apigateway_client.create_integration(
                ApiId=api_id,
                IntegrationType='AWS_PROXY',
                IntegrationUri=lambda_arn,
                PayloadFormatVersion='2.0'
            )
            integration_id = integration_response['IntegrationId']
            print(f"  Integration erstellt für {route_path}")

            route_key = f"{method} {route_path}"
            apigateway_client.create_route(
                ApiId=api_id,
                RouteKey=route_key,
                Target=f"integrations/{integration_id}"
            )
            print(f"  Route erstellt: {route_key}")

            source_arn = f"arn:aws:execute-api:{self.env.region}:{self.env.account}:{api_id}/*/{method}{route_path}"

            try:
                lambda_client.add_permission(
                    FunctionName=lambda_name,
                    StatementId=f"apigateway-{api_id}-{method}-{route_path.replace('/', '-').replace('{', '').replace('}', '')}",
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=source_arn
                )
                print(f"  Lambda Permission hinzugefügt für {lambda_name}")
            except lambda_client.exceptions.ResourceConflictException:
                print(f"  Lambda Permission existiert bereits für {lambda_name}")
            except lambda_client.exceptions.ResourceNotFoundException as e:
                print(f"  Warnung: Lambda Funktion {lambda_name} nicht gefunden, überspringe Permission: {e}")

    def update(self, deployed_tech_id: str, new_value: 'ApiGateway') -> str:
        """Update ein API Gateway"""
        session = boto3.session.Session(
            profile_name=new_value.env.profile,
            region_name=new_value.env.region
        )
        apigateway_client = session.client('apigatewayv2')
        lambda_client = session.client('lambda')

        try:
            apis = apigateway_client.get_apis()
            api_id = None
            for api in apis['Items']:
                if api['Name'] == new_value.api_name:
                    api_id = api['ApiId']
                    break

            if not api_id:
                print(f"API Gateway {new_value.api_name} existiert nicht, erstelle neue...")
                return new_value.create()

            existing_routes = apigateway_client.get_routes(ApiId=api_id)
            for route in existing_routes['Items']:
                apigateway_client.delete_route(ApiId=api_id, RouteId=route['RouteId'])
                print(f"  Route gelöscht: {route['RouteKey']}")

            existing_integrations = apigateway_client.get_integrations(ApiId=api_id)
            for integration in existing_integrations['Items']:
                apigateway_client.delete_integration(ApiId=api_id, IntegrationId=integration['IntegrationId'])
                print(f"  Integration gelöscht")

            new_value._setup_routes(apigateway_client, lambda_client, api_id)

            api_endpoint = f"https://{api_id}.execute-api.{new_value.env.region}.amazonaws.com"
            print(f"API Gateway aktualisiert: {new_value.api_name}")
            print(f"API Endpoint: {api_endpoint}")

            return api_endpoint

        except Exception as e:
            print(f"Fehler beim Update des API Gateway: {e}")
            raise

    def delete(self, tech_id: str):
        """Lösche ein API Gateway"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        apigateway_client = session.client('apigatewayv2')

        try:
            apis = apigateway_client.get_apis()
            api_id = None
            for api in apis['Items']:
                if api['Name'] == self.api_name or self._extract_api_id(tech_id) in api['ApiId']:
                    api_id = api['ApiId']
                    break

            if api_id:
                apigateway_client.delete_api(ApiId=api_id)
                print(f"API Gateway gelöscht: {self.api_name}")
            else:
                print(f"API Gateway nicht gefunden: {self.api_name}")

        except Exception as e:
            print(f"Fehler beim Löschen des API Gateway: {e}")
            raise

    @staticmethod
    def _extract_api_id(endpoint: str) -> str:
        """Extrahiere API ID aus Endpoint URL"""
        if 'https://' in endpoint:
            return endpoint.split('https://')[1].split('.')[0]
        return endpoint

    def __repr__(self) -> str:
        return f"ApiGateway(name='{self.api_name}', routes={len(self.routes)})"
