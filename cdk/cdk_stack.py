import os
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm

)
from constructs import Construct

class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        
        custom_domain = os.getenv('CUSTOM_DOMAIN')
        print(f"CUSTOM_DOMAIN: {os.getenv('CUSTOM_DOMAIN')}")
        print(f"RUNNER_OS: {os.getenv('RUNNER_OS')}")
        print(f"CDK_DEFAULT_ACCOUNT: {os.getenv('CDK_DEFAULT_ACCOUNT')}")
        print(f"CDK_DEFAULT_REGION: {os.getenv('CDK_DEFAULT_REGION')}")
        
        table = dynamodb.Table(self, "urls",
                               partition_key=dynamodb.Attribute(name="key", type=dynamodb.AttributeType.STRING)
        )

        lambda_role = iam.Role(self, "shortener_role",
                               assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                               description="Lambda execution role for the url shortener app"
        )

        lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))

        lambda_role.attach_inline_policy(iam.Policy(self, "allow_access_to_dynamodb",            
                                                        statements=[
                                                            iam.PolicyStatement(
                                                                actions=[
                                                                    "dynamodb:Query",
                                                                    "dynamodb:PutItem"
                                                                ],
                                                                resources=[table.table_arn]
                                                            )
                                                        ]
                                                    )
        )

        lambda_layer = lambda_.LayerVersion(self, "shortener_layer",
                                            code=lambda_.Code.from_asset("resources/layers/"),
                                            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
                                            compatible_architectures=[lambda_.Architecture.X86_64]
        )

        lambda_function = lambda_.Function(self, "shortener_app",
                                           runtime=lambda_.Runtime.PYTHON_3_9,
                                           layers=[lambda_layer],
                                           code=lambda_.Code.from_asset("resources/shortener_app/"),
                                           handler="main.handler",
                                           role=lambda_role,
                                           timeout=Duration.minutes(1),
                                           memory_size=128,
                                           environment={
                                            "TABLE": table.table_name
                                           }
        )

        hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone", domain_name=custom_domain)
        # hosted_zone = route53.HostedZone(self, "HostedZone", zone_name=custom_domain)
        # hosted_zone.apply_removal_policy(RemovalPolicy.DESTROY)



        certificate = acm.DnsValidatedCertificate(
            self,
            "ApiCertificate",
            domain_name=f"api.{custom_domain}",
            hosted_zone=hosted_zone,
            region="us-east-1",
        )

        api = apigateway.LambdaRestApi(self, "shortener_api",
                                       handler=lambda_function,
                                       proxy=True,
                                    #    endpoint_types=[apigateway.EndpointType.REGIONAL],
                                       domain_name=apigateway.DomainNameOptions(
                                            domain_name=f"api.{custom_domain}",
                                            certificate=certificate,
                                            security_policy=apigateway.SecurityPolicy.TLS_1_2,
                                            endpoint_type=apigateway.EndpointType.EDGE
                                       )
        )

        api.root.add_method("GET")
        api.root.add_method("POST")


        route53.ARecord(
            self,
            "ApiRecord",
            record_name="api",
            zone=hosted_zone,
            target=route53.RecordTarget.from_alias(targets.ApiGateway(api)),
        )