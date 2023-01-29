from aws_cdk import (
    Stack, Tags, RemovalPolicy, Duration, CfnOutput
)
from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_route53 import HostedZone
from aws_cdk.aws_s3 import Bucket, BlockPublicAccess, BucketEncryption, LifecycleRule, Transition, StorageClass
from aws_cdk.aws_lambda import Function, Runtime, Code
from constructs import Construct


class R53Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        Tags.of(self).add("project", props["namespace"])
        namespace = props["namespace"]

        # Route53 S3 Backup Bucket
        backup_bucket = Bucket(self, "R53BackupBucket",
                               block_public_access=BlockPublicAccess.BLOCK_ALL,
                               encryption=BucketEncryption.S3_MANAGED,
                               enforce_ssl=True,
                               versioned=True,
                               removal_policy=RemovalPolicy.RETAIN,
                               lifecycle_rules=[LifecycleRule(transitions=[
                                   Transition(storage_class=StorageClass.INTELLIGENT_TIERING,
                                              transition_after=Duration.days(30))
                               ])]
                               )

        # Import the Amazon Route53 Zone
        zone_name = props["hosted_zone_name"]
        zone_id = props["hosted_zone_id"]
        route53_zone_import = HostedZone.from_hosted_zone_attributes(self, "ImportedBackupZone",
                                                                     hosted_zone_id=zone_id,
                                                                     zone_name=zone_name)

        # Create the Lambda function to facilitate all of this
        r53_backup_func = Function(self, "R53_import_function", runtime=Runtime.PYTHON_3_9,
                                   handler="r53_lambda_function.lambda_handler",
                                   code=Code.from_asset(path="infra/functions"),
                                   environment={
                                       "s3_bucket_name": backup_bucket.bucket_name,
                                       "s3_bucket_region": self.region,
                                       "r53_zone_id": route53_zone_import.hosted_zone_id
                                   }
                                   )

        # Set the AWS IAM permissions for a role to execute
        backup_bucket.grant_read_write(r53_backup_func.role)
        r53_backup_func.role.add_to_principal_policy(PolicyStatement(actions=["route53:Get*"],
                                                                     resources=[
                                                                         f"{route53_zone_import.hosted_zone_arn}"]))

        # Outputs

        CfnOutput(self, "R53BackupBucketName", value=backup_bucket.bucket_name, description="The name of the Amazon S3 "
                                                                                            "Bucket",
                  export_name="R53BackupBucket")
