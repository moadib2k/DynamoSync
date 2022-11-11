from submit_firehose import lambda_handler
import json

f = open('F:\dev\mrb\DynamoSync\src\stream_lambda\SampleDelete.json')
data = json.load(f)
lambda_handler(data, None)

