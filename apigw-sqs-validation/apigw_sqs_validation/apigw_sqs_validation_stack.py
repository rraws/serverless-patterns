from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_sqs as sqs,
    aws_iam as iam,
    Duration,
    CfnOutput
)
from constructs import Construct


class SqsValidationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Step 1: Create SQS Queue
        queue = sqs.Queue(
            self, "ValidatedMessagesQueue",
            queue_name="validated-messages-queue",
            visibility_timeout=Duration.seconds(300)
        )

        # Step 2 & 3: Create REST API and Request Model
        api = apigateway.RestApi(
            self, "SqsValidationApi",
            rest_api_name="sqs-validation-api",
            description="API Gateway with payload validation for SQS"
        )

        # Create the message model for validation
        message_model = api.add_model(
            "MessageModel",
            content_type="application/json",
            model_name="MessageModel",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="MessageModel",
                type=apigateway.JsonSchemaType.OBJECT,
                required=["userId", "message"],
                properties={
                    "userId": {"type": apigateway.JsonSchemaType.STRING},
                    "message": {"type": apigateway.JsonSchemaType.STRING}
                },
                additional_properties=False
            )
        )

        # Step 4 & 5: Create Resource, Method and Request Validation
        messages_resource = api.root.add_resource("messages")

        # Create IAM role for API Gateway to SQS
        sqs_role = iam.Role(
            self, "ApiGatewayToSQSRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com")
        )
        queue.grant_send_messages(sqs_role)

        # Step 6: Configure Integration Request
        integration = apigateway.AwsIntegration(
            service="sqs",
            path=f"{self.account}/{queue.queue_name}",
            integration_http_method="POST",
            options=apigateway.IntegrationOptions(
                credentials_role=sqs_role,
                request_templates={
                    "application/json": f'''#set($messageBody = $input.json('$'))
Action=SendMessage&MessageBody=$util.urlEncode($messageBody)&QueueUrl={queue.queue_url}'''
                },
                integration_responses=[{
                    "statusCode": "200",
                    "responseTemplates": {
                        "application/json": '''{
                            "messageId": "$input.path('$.SendMessageResponse.SendMessageResult.MessageId')",
                            "status": "success"
                        }'''
                    }
                }]
            )
        )

        # Add method with validation
        messages_resource.add_method(
            "POST",
            integration,
            request_validator=apigateway.RequestValidator(
                self, "MessageValidator",
                rest_api=api,
                validate_request_body=True,
                validate_request_parameters=False
            ),
            request_models={"application/json": message_model},
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    # response_models={
                    #     "application/json": apigateway.Model.EMPTY_MODEL
                    # }
                )
            ]
        )

        # Output the API URL
        CfnOutput(
            self, "ApiEndpoint",
            value=f"{api.url}messages",
            description="API Endpoint URL"
        )
