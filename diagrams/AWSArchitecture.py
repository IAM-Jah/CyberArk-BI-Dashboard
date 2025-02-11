from diagrams import Diagram, Cluster
from diagrams.aws.network import VPC, PrivateSubnet, PublicSubnet, InternetGateway, NATGateway
from diagrams.aws.compute import EC2, Lambda
from diagrams.aws.storage import S3
from diagrams.aws.database import RDS
from diagrams.aws.analytics import Quicksight
from diagrams.aws.security import SecretsManager
from diagrams.aws.integration import Eventbridge, SNS
from diagrams.aws.management import Cloudwatch
from diagrams.generic.os import RedHat, Windows
from diagrams.k8s.controlplane import API

# Diagram generation
with Diagram("CyberArk Business Intelligence with AWS", show=True):

    # Networking
    with Cluster("Project VPC"):

        with Cluster("Public Subnet"):
            bastion_host = EC2("Bastion Host")

        with Cluster("Private Subnet"):
            lambda_functions = Lambda("Lambda ETL Functions")
            rds = RDS("RDS - PSQL")

    # Data Ingest and Storage
    with Cluster("On-Prem Environment"):
        component_server = Windows("REST API Ingest")
        psmp_server = RedHat("Log ingest")
        ccp = API("CyberArk CCP")

    s3_bucket = S3("S3 Ingest")
    secrets_manager = SecretsManager("Secrets Manager")
    
    # Orchestration and Monitoring
    eventbridge = Eventbridge("EventBridge Scheduler")
    cloudwatch = Cloudwatch("CloudWatch Logs & Alerts")
    sns = SNS("SNS Notifications")

    # Data Visualization
    quicksight = Quicksight("QuickSight")

    # Relationships and interactions
    bastion_host >> rds
    lambda_functions >> rds
    lambda_functions >> s3_bucket
    lambda_functions >> cloudwatch
    lambda_functions >> secrets_manager
    eventbridge >> lambda_functions
    rds >> secrets_manager
    quicksight >> rds
    cloudwatch >> sns
    component_server >> s3_bucket
    component_server >> ccp
    psmp_server >> s3_bucket
    psmp_server >> ccp