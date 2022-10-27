import aws_cdk as core
import aws_cdk.assertions as assertions

from dyanmo_sink.dyanmo_sink_stack import DyanmoSinkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in dyanmo_sink/dyanmo_sink_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = DyanmoSinkStack(app, "dyanmo-sink")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
