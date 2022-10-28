import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_redshift as redshift,
    aws_ec2 as ec2,
    aws_secretsmanager as sm,
    aws_iam as iam
)
from constructs import Construct

class DynamoSyncStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create the vpc for the redshift cluster
        vpc = ec2.Vpc(
            self, 
            "sync-stack-demo-vpc",
            cidr="10.3.0.0/16",
            max_azs=2,
            nat_gateways=0,
            enable_dns_support=True,
            enable_dns_hostnames=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public", cidr_mask=24, subnet_type=ec2.SubnetType.PUBLIC),
                ec2.SubnetConfiguration(name="redshift", cidr_mask=24, subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
            ]
        )

        cluster_secret = sm.Secret(
            self,
            "sync-stack-redshift-cluster-secret",
            description="Redshift Cluster Secret",
            secret_name="/sync-stack/Redshift",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            generate_secret_string= sm.SecretStringGenerator(
                exclude_characters ="'\"\\/@"
            )
        )

        rs_cluster_role = iam.Role(
                self, 
                "sync-stack-redshift-cluster-role",
                assumed_by=iam.ServicePrincipal("redshift.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AmazonS3ReadOnlyAccess"
                )
            ]
        )

        cluster_subnet_group = redshift.CfnClusterSubnetGroup(
            self,
            "sync-stack-redshift-cluster-subnet-group",
            subnet_ids=vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC).subnet_ids,
            description="Sync Stack Redshift Cluster Subnet Group"
        )
        
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
        redshift_cluster=redshift.CfnCluster(
            self,
            "sync-stack-redshift-cluster",
            cluster_type="single-node",
            db_name="sink-stack",
            master_username="dwh_user",
            master_user_password=cluster_secret.secret_value.unsafe_unwrap(),
            iam_roles=[rs_cluster_role.role_arn],
            node_type="dc2.large",
            cluster_subnet_group_name=cluster_subnet_group.ref,
            #vpc_security_group_ids=[
            #    quicksight_to_redshift_sg.security_group_id]
        )
