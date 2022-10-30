from fnmatch import translate
import json
import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_redshift as redshift,
    aws_redshift_alpha as redshift_alpha,
    aws_ec2 as ec2,
    aws_secretsmanager as sm,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_kinesis as kns,
    aws_lambda_event_sources as event_sources
)
from constructs import Construct

class DynamoSyncStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ##############################
        #
        # DYNAMO
        #
        ##############################
        
        # create the dynamo kinesis stream
        dynamoStream = kns.Stream(
            self, 
            "sync-stack-dynamo-stream",
            stream_name="sync_stack_dynamo_stream",
            retention_period=cdk.Duration.hours(24),
            stream_mode=kns.StreamMode.ON_DEMAND,
            encryption=kns.StreamEncryption.UNENCRYPTED)

        # create the dynamo table
        dynamoTable = dynamodb.Table(self,
            'sync-stack-dynamo-table',
            table_name='sync-stack-table',
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            partition_key=dynamodb.Attribute(name='Id', type=dynamodb.AttributeType.STRING),
            kinesis_stream=dynamoStream,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES)

        ##############################
        #
        # Transform Lambda
        #
        ##############################

        transform_role = iam.Role(
                self, 
                "sync-stack-lambda-role",
                role_name="sync-stack-lambda-role",
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
                ]
            )


        # create the function that will read events from the dynamo kinesis stream
        transform_lambda = _lambda.Function(self, 
                       'sync-stack-lambda',
                       function_name='sync-stack-lambda',
                       runtime=_lambda.Runtime.PYTHON_3_9,
                       code=_lambda.Code.from_asset(os.path.join(os.getcwd(),'src/stream_lambda/')),
                       handler='submit_firehose.lambda_handler',
                       role=transform_role)

        # add the event source tying the lambda function to the dynamo stream        
        transform_lambda.add_event_source(
            event_sources.DynamoEventSource(
                dynamoTable,
                starting_position=_lambda.StartingPosition.LATEST,
                batch_size=1)
            )
        

        ##############################
        #
        # REDSHIFT
        #
        ##############################

        # Create the password for the cluster admin
        cluster_secret = sm.Secret(
            self,
            "sync-stack-redshift-cluster-secret",
            description="Redshift Cluster Secret",
            secret_name="/sync-stack/Redshift",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            generate_secret_string= sm.SecretStringGenerator(
                exclude_characters ="'\"\\/@",
                exclude_punctuation=True
            )
        )

        # create the secret for a database login 
        user_secret = sm.Secret(
            self,
            "sync-stack-redshift-user-secret",
            description="Redshift User Secret",
            secret_name="/sync-stack/Redshift/User",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            generate_secret_string= sm.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "rsuser"}),
                generate_string_key="password",
                exclude_characters ="'\"\\/@",
                exclude_punctuation=True
            )
        )
                
        # create the vpc for the redshift cluster
        cluster_vpc = ec2.Vpc(
            self, 
            "sync-stack-redshift-vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.3.0.0/16"),
            max_azs=2,
            nat_gateways=0,
            enable_dns_support=True,
            enable_dns_hostnames=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public", cidr_mask=24, subnet_type=ec2.SubnetType.PUBLIC),
                ec2.SubnetConfiguration(name="redshift", cidr_mask=24, subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
            ]
        )

        # create the IAM role for the cluster
        cluster_role = iam.Role(
                self, 
                "sync-stack-redshift-cluster-role",
                assumed_by=iam.ServicePrincipal("redshift.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonRedshiftAllCommandsFullAccess")
                ]
            )

        # create the subnet for the cluster
        cluster_subnet_group = redshift_alpha.ClusterSubnetGroup(
            self,
            "sync-stack-redshift-cluster-subnet-group",
            description="Sync Stack Redshift Cluster Subnet Group",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            vpc=cluster_vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )

        # create the actual cluster
        redshift_cluster=redshift_alpha.Cluster(
            self,
            "sync-stack-redshift-cluster",
            cluster_type=redshift_alpha.ClusterType.SINGLE_NODE,
            cluster_name="sync-stack-cluster",
            master_user = redshift_alpha.Login(
                master_username="admin",
                master_password=cluster_secret.secret_value
            ),
            node_type=redshift_alpha.NodeType.DC2_LARGE,
            subnet_group=cluster_subnet_group,
            vpc=cluster_vpc,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            roles=[cluster_role]
        )


        ##############################
        #
        # Redshift Ingest Stream
        #
        ##############################

        # create the kinesis stream for redshift
        ingest_stream = kns.Stream(
            self,
            "sync-stack-ingest-stream",
            stream_name="sync_stack_ingest_stream",
            retention_period=cdk.Duration.hours(24),
            stream_mode=kns.StreamMode.ON_DEMAND,
            encryption=kns.StreamEncryption.UNENCRYPTED
        )

        # allow the cluster to read the stream
        ingest_stream.grant_read(cluster_role)

        # allow the transform lamgda to write to the stream
        ingest_stream.grant_write(transform_lambda)


        #table = redshift_alpha.Table(
        #        self,
        #        id='sync-stack-redshift-table',
        #        table_name='sync',
        #        cluster=redshift_cluster,
        #        database_name='sync-db',
        #        dist_style=redshift_alpha.TableDistStyle.KEY,
        #        table_columns = [
        #            redshift_alpha.Column(name="id", data_type='varchar(36)', dist_key=True)
        #            ],
        #        admin_user=cluster_secret
        #        )


        #cluster_subnet_group = redshift.CfnClusterSubnetGroup(
        #    self,
        #    "sync-stack-redshift-cluster-subnet-group",
        #    subnet_ids=cluster_vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC).subnet_ids,
        #    description="Sync Stack Redshift Cluster Subnet Group"
        #)


        
        ##Create Security Group for QuickSight
        #quicksight_to_redshift_sg = _ec2.SecurityGroup(
        #    self,
        #    id="redshiftSecurityGroup",
        #    vpc=vpc.get_vpc,
        #    security_group_name=f"redshift_sg_{id}",
        #    description="Security Group for Quicksight"
        #)

        ## https://docs.aws.amazon.com/quicksight/latest/user/regions.html
        #quicksight_to_redshift_sg.add_ingress_rule(
        #    peer=_ec2.Peer.ipv4("52.23.63.224/27"),
        #    connection=_ec2.Port.tcp(5439),
        #    description="Allow QuickSight connetions"
        #)

        #redshift_cluster=redshift.CfnCluster(
        #    self,
        #    "sync-stack-redshift-cluster",
        #    cluster_type="single-node",
        #    db_name="sink-stack",
        #    master_username="dwh_user",
        #    master_user_password=cluster_secret.secret_value.unsafe_unwrap(),
        #    iam_roles=[rs_cluster_role.role_arn],
        #    node_type="dc2.large",
        #    cluster_subnet_group_name=cluster_subnet_group.ref,
        #    #vpc_security_group_ids=[
        #    #    quicksight_to_redshift_sg.security_group_id]
        #)
        
