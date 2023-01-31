
# Amazon Route53 Backup

## Overview
This solution deploys an AWS Lambda function that runs at 03:00AM EST (08:00 UTC) daily and backs up all of your Amazon Route53 zones and records daily. The zones and its contents are saved as both `.json` and `.csv` in Amazon S3 and are storage-tiered after 30 days, along with expiring after 1yr. You are welcome to change any of the values!

## Requirements
1. Install `aws-cdk` if you haven't already (AWS CDK v2.x): https://aws.amazon.com/cdk/
2. Run `cdk deploy`
3. Use the CloudFormation outputs to view the Amazon S3 output bucket, to view the backed up records
4. Subscribe to the `AlertTopic` (as shown below) for Lambda function invocation errors/etc. 

## Diagram
![Diagram](img/diagram.png)

## Additional Information
Come visit us at https://www.troydieter.com or open a PR! Thanks!