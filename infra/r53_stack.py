from aws_cdk import (
    Stack, Tags, RemovalPolicy, Duration, CfnOutput
)
from aws_cdk.aws_events import Rule, Schedule, EventPattern
from aws_cdk.aws_iam import ManagedPolicy
from aws_cdk.aws_lambda import Function, Runtime, Code
from aws_cdk.aws_s3 import Bucket, BlockPublicAccess, BucketEncryption, LifecycleRule, Transition, StorageClass
from aws_cdk.aws_events_targets import LambdaFunction, SnsTopic
from aws_cdk.aws_sns import Topic
from constructs import Construct


class R53Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        namespace = props["namespace"]
        Tags.of(self).add("project", namespace)

        # Route53 S3 Backup Bucket
        # noinspection PyTypeChecker
        backup_bucket = Bucket(self, "R53BackupBucket",
                               block_public_access=BlockPublicAccess.BLOCK_ALL,
                               encryption=BucketEncryption.S3_MANAGED,
                               enforce_ssl=True,
                               versioned=True,
                               removal_policy=RemovalPolicy.RETAIN,
                               lifecycle_rules=[LifecycleRule(transitions=[
                                   Transition(storage_class=StorageClass.INTELLIGENT_TIERING,
                                              transition_after=Duration.days(30))
                               ])],
                               )

        # Create the Lambda function to facilitate all of this
        r53_backup_func = Function(self, "R53_import_function", runtime=Runtime.PYTHON_3_9,
                                   handler="r53_lambda_function.lambda_handler",
                                   code=Code.from_asset(path="infra/functions"),
                                   environment={
                                       "s3_bucket_name": backup_bucket.bucket_name,
                                       "s3_bucket_region": self.region
                                   }
                                   )

        # Set the AWS IAM permissions for a role to execute
        backup_bucket.grant_read_write(r53_backup_func.role)
        r53_read_only_pol = ManagedPolicy.from_aws_managed_policy_name('AmazonRoute53ReadOnlyAccess')
        r53_backup_func.role.add_managed_policy(r53_read_only_pol)

        # Create the SNS topic to send notifications to
        r53_backup_topic = Topic(self, "R53BackupTopic")
        r53_backup_topic.grant_publish(r53_backup_func.role)

        # Create the EventBridge rules
        backup_frequency_rule = Rule(
            self,
            "Run Daily at 21:00 hrs UTC",
            schedule=Schedule.cron(minute="00", hour="21", week_day="*", month="*", year="*"),
        )

        backup_frequency_rule.add_target(LambdaFunction(r53_backup_func))

        failure_notification_rule = Rule(self, "R53BackupFailureNotification",
                                         event_pattern=EventPattern(
                                             source=["aws.lambda"],
                                             detail_type=["AWS API Call via CloudTrail"],
                                             detail={
                                                 "eventName": ["CreateFunction"],
                                                 "requestParameters": {
                                                     "functionName": r53_backup_func.function_name
                                                 },
                                                 "errorMessage": ".*"
                                             }
                                         ),
                                         targets=[SnsTopic(topic=r53_backup_topic)])

        # Outputs

        CfnOutput(self, "R53BackupBucketName", value=backup_bucket.bucket_name, description="The name of the Amazon S3 "
                                                                                            "Bucket",
                  export_name="R53BackupBucket")
