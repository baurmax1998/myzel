import json

import boto3

from src.model import AwsEnviroment, Resources
from src.model.registry import register_resource


@register_resource("iam_role")
class IamRole(Resources):
    """IAM Role Resource für AWS IAM Management"""

    def __init__(
        self,
        role_name: str,
        assume_role_policy: dict,
        env: AwsEnviroment,
        managed_policies: list = None,
        inline_policies: dict = None,
        description: str = ""
    ):
        self.role_name = role_name
        self.assume_role_policy = assume_role_policy
        self.env = env
        self.managed_policies = managed_policies or []
        self.inline_policies = inline_policies or {}
        self.description = description

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'IamRole':
        """Hole eine spezifische IAM Role"""
        role_name = cls._extract_role_name(tech_id)
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        iam_client = session.client('iam')

        try:
            response = iam_client.get_role(RoleName=role_name)
            role = response['Role']

            attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
            managed_policies = [p['PolicyArn'] for p in attached_policies['AttachedPolicies']]

            inline_policies_response = iam_client.list_role_policies(RoleName=role_name)
            inline_policies = {}
            for policy_name in inline_policies_response['PolicyNames']:
                policy_response = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                inline_policies[policy_name] = policy_response['PolicyDocument']

            return cls(
                role_name=role['RoleName'],
                assume_role_policy=role['AssumeRolePolicyDocument'],
                env=env,
                managed_policies=managed_policies,
                inline_policies=inline_policies,
                description=role.get('Description', '')
            )
        except iam_client.exceptions.NoSuchEntityException:
            return cls(
                role_name=role_name,
                assume_role_policy={},
                env=env
            )
        except Exception as e:
            print(f"Fehler beim Abrufen der IAM Role {role_name}: {e}")
            raise

    def create(self) -> str:
        """Erstelle eine neue IAM Role oder verwende existierende"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        iam_client = session.client('iam')

        try:
            existing_role = iam_client.get_role(RoleName=self.role_name)
            print(f"IAM Role existiert bereits: {self.role_name}")
            arn = existing_role['Role']['Arn']
        except iam_client.exceptions.NoSuchEntityException:
            create_role_params = {
                'RoleName': self.role_name,
                'AssumeRolePolicyDocument': json.dumps(self.assume_role_policy)
            }
            if self.description:
                create_role_params['Description'] = self.description

            response = iam_client.create_role(**create_role_params)
            arn = response['Role']['Arn']
            print(f"IAM Role erstellt: {self.role_name}")
            print(f"ARN: {arn}")

        self._sync_policies(iam_client)
        self._wait_for_propagation(iam_client)

        return arn

    def _sync_policies(self, iam_client, role_name: str = None):
        """Synchronisiere Policies mit gewünschtem Zustand

        Args:
            iam_client: boto3 IAM client
            role_name: Optional role name to sync (defaults to self.role_name)
        """
        target_role_name = role_name or self.role_name

        current_managed = iam_client.list_attached_role_policies(RoleName=target_role_name)
        current_policy_arns = {p['PolicyArn'] for p in current_managed['AttachedPolicies']}
        new_policy_arns = set(self.managed_policies)

        for policy_arn in current_policy_arns - new_policy_arns:
            iam_client.detach_role_policy(RoleName=target_role_name, PolicyArn=policy_arn)
            print(f"  Managed Policy detached: {policy_arn}")

        for policy_arn in new_policy_arns - current_policy_arns:
            iam_client.attach_role_policy(RoleName=target_role_name, PolicyArn=policy_arn)
            print(f"  Managed Policy attached: {policy_arn}")

        current_inline = iam_client.list_role_policies(RoleName=target_role_name)
        current_inline_names = set(current_inline['PolicyNames'])
        new_inline_names = set(self.inline_policies.keys())

        for policy_name in current_inline_names - new_inline_names:
            iam_client.delete_role_policy(RoleName=target_role_name, PolicyName=policy_name)
            print(f"  Inline Policy gelöscht: {policy_name}")

        for policy_name in new_inline_names:
            iam_client.put_role_policy(
                RoleName=target_role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(self.inline_policies[policy_name])
            )
            if policy_name in current_inline_names:
                print(f"  Inline Policy aktualisiert: {policy_name}")
            else:
                print(f"  Inline Policy erstellt: {policy_name}")

    def update(self, deployed_tech_id: str, new_value: 'IamRole') -> str:
        """Update eine IAM Role"""
        deployed_role_name = self._extract_role_name(deployed_tech_id)

        session = boto3.session.Session(
            profile_name=new_value.env.profile,
            region_name=new_value.env.region
        )
        iam_client = session.client('iam')

        # If the role name changed, create a new role instead of updating
        if deployed_role_name != new_value.role_name:
            print(f"IAM Role name changed ({deployed_role_name} → {new_value.role_name}), erstelle neue...")
            return new_value.create()

        try:
            response = iam_client.get_role(RoleName=deployed_role_name)
            arn = response['Role']['Arn']
        except iam_client.exceptions.NoSuchEntityException:
            print(f"IAM Role {deployed_role_name} existiert nicht, erstelle neue...")
            return new_value.create()

        current_assume_policy = json.dumps(response['Role']['AssumeRolePolicyDocument'], sort_keys=True)
        new_assume_policy = json.dumps(new_value.assume_role_policy, sort_keys=True)

        if current_assume_policy != new_assume_policy:
            iam_client.update_assume_role_policy(
                RoleName=deployed_role_name,
                PolicyDocument=json.dumps(new_value.assume_role_policy)
            )
            print(f"Assume Role Policy aktualisiert: {deployed_role_name}")

        new_value._sync_policies(iam_client, role_name=deployed_role_name)

        if new_value.description and new_value.description != response['Role'].get('Description', ''):
            iam_client.update_role_description(
                RoleName=deployed_role_name,
                Description=new_value.description
            )
            print(f"Description aktualisiert: {deployed_role_name}")

        # Wait for role to be fully propagated after updates
        new_value._wait_for_propagation(iam_client)

        print(f"IAM Role erfolgreich aktualisiert: {deployed_role_name}")
        return arn

    def delete(self, tech_id: str):
        """Lösche eine IAM Role"""
        role_name = self._extract_role_name(tech_id)

        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        iam_client = session.client('iam')

        try:
            attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
            for policy in attached_policies['AttachedPolicies']:
                iam_client.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy['PolicyArn']
                )
                print(f"  Managed Policy detached: {policy['PolicyArn']}")

            inline_policies = iam_client.list_role_policies(RoleName=role_name)
            for policy_name in inline_policies['PolicyNames']:
                iam_client.delete_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                print(f"  Inline Policy gelöscht: {policy_name}")

            iam_client.delete_role(RoleName=role_name)
            print(f"IAM Role gelöscht: {role_name}")

        except iam_client.exceptions.NoSuchEntityException:
            print(f"IAM Role existiert nicht: {role_name}")
        except Exception as e:
            print(f"Fehler beim Löschen der IAM Role: {e}")
            raise

    def _wait_for_propagation(self, iam_client):
        """Warte bis IAM Role vollständig propagiert ist"""
        import time
        max_attempts = 60
        for attempt in range(max_attempts):
            try:
                iam_client.get_role(RoleName=self.role_name)
                if attempt > 0:
                    print(f"IAM Role propagiert und bereit")
                return
            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(1)
                else:
                    print(f"Warnung: Role Propagation timeout, fortfahren...")
                    return

    def get_arn(self) -> str:
        """Get ARN for this role

        Returns the actual ARN from AWS if available (set via set_tech_id),
        otherwise generates it from the role name.
        """
        # If we have a stored tech_id (actual ARN from AWS), use it
        if self._tech_id:
            return self._tech_id
        # Otherwise generate from role name
        return f"arn:aws:iam::{self.env.account}:role/{self.role_name}"

    @staticmethod
    def _extract_role_name(arn: str) -> str:
        """Extrahiere Role Name aus ARN"""
        return arn.split('/')[-1]

    def __repr__(self) -> str:
        return f"IamRole(name='{self.role_name}')"
