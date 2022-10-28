#!/usr/bin/env python3
import os

import aws_cdk as cdk

from dynamo_sink.dynamo_sync_stack import DynamoSyncStack


app = cdk.App()
DynamoSyncStack(app, "dynamo-sink", env=cdk.Environment(
                account="444372120632",
                region="us-west-1"))

app.synth()
