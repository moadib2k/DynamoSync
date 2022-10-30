#!/usr/bin/env python3
import os

import aws_cdk as cdk

from dynamo_sync.dynamo_sync_stack import DynamoSyncStack


app = cdk.App()
DynamoSyncStack(app, "dynamo-sync")

app.synth()
