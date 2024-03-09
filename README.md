
# Amazon Route53 Backup

## Overview
This solution deploys an AWS Lambda function that runs at 08:00 UTC daily and backs up all of your Amazon Route53 zones and records daily. The zones and its contents are saved as both `.json` and `.csv` in Amazon S3 and are storage-tiered after 30 days, along with expiring after 1yr.

## Operation
1. The AWS-CDK deployment will output an Amazon S3 bucket, such as: `R53BackupStack.R53BackupBucketName = r53backupstack-r53backupbucketf9166e0f-o2ohsku2jmbz` - look here for the backed up objects after the first run at 03:00 UTC
2. The Amazon S3 object structure will be categorized by timestamped folders (eg. `2024-03-07_06-50-40/`)
3. You'll see Amazon S3 objects (directories) such as: `troydieter.com_public/`
4. Within those respective directories you'll see the name and `.csv` or `.json` (eg. `troydieter.com.csv`)
5. Utilize these files to restore your Amazon Route53 records as needed.

## Timing
This will run daily at `08:00` UTC (03:00AM EST) - If you'd like to change the timing, refer to `cdk.json` and adjust the `schedule_` parameters. More info is available here: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_events/Schedule.html

## Lifecycle Rules
### Bucket Configuration

- **Block Public Access**: All public access to the bucket is blocked to ensure data privacy and security.
- **Encryption**: Objects stored in the bucket are encrypted using Amazon S3-managed encryption keys (SSE-S3).
- **Enforce SSL**: All requests to the bucket are enforced to use SSL/TLS encryption for secure communication.
- **Versioning**: Object versioning is enabled to maintain multiple versions of objects in the bucket.
- **Removal Policy**: The bucket is configured with a retention policy set to `Retain`, ensuring that the bucket contents are retained even if the stack is deleted.

### Lifecycle Rules

#### Transition Rule

- **Purpose**: Automatically transitions objects to the Intelligent-Tiering storage class after 30 days.
- **Action**: Objects are moved to the Intelligent-Tiering storage class, which optimizes storage costs by automatically moving objects between different tiers based on access patterns.

#### Expiration Rule

- **Purpose**: Defines a lifecycle policy to expire objects after 365 days.
- **Action**: Objects older than 365 days are automatically deleted from the bucket, helping to manage storage costs and ensure compliance with data retention policies.

## Requirements
1. Install `aws-cdk` if you haven't already (AWS CDK v2.x): https://aws.amazon.com/cdk/
2. Run `cdk deploy`
3. Use the CloudFormation outputs to view the Amazon S3 output bucket, to view the backed up records
4. Subscribe to the `AlertTopic` (as shown below) for Lambda function invocation errors/etc. 

## Diagram
![Diagram](img/diagram.png)

## Additional Information
Come visit us at https://www.troydieter.com or open a PR! Thanks!