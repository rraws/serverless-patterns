#!/usr/bin/env python3
import os

import aws_cdk as cdk

from apigw_sqs_validation.apigw_sqs_validation_stack import SqsValidationStack


app = cdk.App()
SqsValidationStack(app, "SqsValidationStack")
app.synth()
