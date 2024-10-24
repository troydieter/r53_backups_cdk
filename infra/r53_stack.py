from aws_cdk import (
    Stack, Tags, RemovalPolicy, Duration, CfnOutput
)
from aws_cdk.aws_events import Rule, Schedule
from aws_cdk.aws_events_targets import LambdaFunction
from aws_cdk.aws_iam import ManagedPolicy
from aws_cdk.aws_lambda import Function, Runtime, Code
from aws_cdk.aws_s3 import Bucket, BlockPublicAccess, BucketEncryption, LifecycleRule, Transition, StorageClass
from aws_cdk.aws_sns import Topic
from aws_cdk.aws_sns_subscriptions import EmailSubscription
from cdk_watchful import Watchful
from constructs import Construct


class R53Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        namespace = props["namespace"]
        schedule_minute = props["schedule_minute"]
        schedule_hour = props["schedule_hour"]
        schedule_week_day = props["schedule_week_day"]
        schedule_month = props["schedule_month"]
        schedule_year = props["schedule_year"]
        Tags.of(self).add("project", namespace)

        # Amazon SNS Topic for alerting events
        notification_topic = Topic(self, "AlertTopic", display_name=f"Alert Topic for {namespace}")

        # Monitoring
        wf = Watchful(self, "Watchful", alarm_sns=notification_topic, dashboard_name=f"{namespace}-r53-dashboard")
        wf.watch_scope(self)

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
                               ]), LifecycleRule(expiration=Duration.days(365))],
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

        # Create the EventBridge rules
        backup_frequency_rule = Rule(
            self,
            f"Route53 Backup Function - Recurring: {schedule_hour}:{schedule_minute} - {schedule_month}:{schedule_week_day}:{schedule_year}",
            schedule=Schedule.cron(minute=schedule_minute, hour=schedule_hour, week_day=schedule_week_day, month=schedule_month, year=schedule_year)
        )

        backup_frequency_rule.add_target(LambdaFunction(r53_backup_func))

        # Outputs

        CfnOutput(self, "R53BackupBucketName", value=backup_bucket.bucket_name, description="The name of the Amazon S3 "
                                                                                            "Bucket",
                  export_name="R53BackupBucket")
