from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb

)
from constructs import Construct

class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

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
                                           environment={
                                            "TABLE": table.table_name
                                           }
        )
            
        api = apigateway.LambdaRestApi(self, "shortener_api",
                                       handler=lambda_function,
                                       proxy=True,
                                       endpoint_types=[apigateway.EndpointType.REGIONAL]
        )

        api.root.add_method("GET")
        api.root.add_method("POST")
