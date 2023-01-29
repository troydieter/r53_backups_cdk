"""AWS Route 53 Lambda Backup"""

import csv
import json
import os
import time
from typing import Optional, Tuple, List

import boto3

try:
    s3_bucket_name = os.environ['s3_bucket_name']
    s3_bucket_region = os.environ['s3_bucket_region']
except KeyError as e:
    print("Warning: Environmental variable(s) not defined")

# Create client objects

s3 = boto3.client('s3', region_name=s3_bucket_region)
route53 = boto3.client('route53')


# Functions
def upload_to_s3(folder: str, filename: str, bucket_name: str, key: str) -> None:
    """Upload a file to a folder in an Amazon S3 bucket."""
    key = folder + "/" + key
    try:
        s3.upload_file(str(filename), bucket_name, key)
        print(f"Uploaded {filename} to {bucket_name}/{key}")
    except Exception as e:
        raise Exception(f"Failed to upload {filename} to S3 bucket {bucket_name} due to {e}")


def get_route53_hosted_zones(next_zone: Optional[Tuple[str, str]] = None) -> List[dict]:
    """Recursively returns a list of hosted zones in Amazon Route 53."""
    try:
        if next_zone:
            response = route53.list_hosted_zones_by_name(
                DNSName=next_zone[0],
                HostedZoneId=next_zone[1]
            )
        else:
            response = route53.list_hosted_zones_by_name()
    except Exception as e:
        raise Exception(f"Failed to list hosted zones due to {e}")

    hosted_zones = response['HostedZones']
    # if response is truncated, call function again with next zone name/id
    if response['IsTruncated']:
        hosted_zones += get_route53_hosted_zones(
            (response['NextDNSName'],
             response['NextHostedZoneId'])
        )
    return hosted_zones


def get_route53_zone_records(zone_id: str, next_record: Optional[Tuple[str, str]] = None) -> List[dict]:
    """Recursively returns a list of records of a hosted zone in Route 53."""
    try:
        if next_record:
            response = route53.list_resource_record_sets(
                HostedZoneId=zone_id,
                StartRecordName=next_record[0],
                StartRecordType=next_record[1]
            )
        else:
            response = route53.list_resource_record_sets(HostedZoneId=zone_id)
    except Exception as e:
        raise Exception(f"Failed to list zone records due to {e}")

    zone_records = response['ResourceRecordSets']
    # if response is truncated, call function again with next record name/id
    if response['IsTruncated']:
        zone_records += get_route53_zone_records(
            zone_id,
            (response['NextRecordName'],
             response['NextRecordType'])
        )
    return zone_records


def get_record_value(record):
    """Return a list of values for a hosted zone record."""
    # test if record's value is Alias or dict of records
    try:
        value = [':'.join(
            ['ALIAS', record['AliasTarget']['HostedZoneId'],
             record['AliasTarget']['DNSName']]
        )]
    except KeyError:
        value = []
        for v in record['ResourceRecords']:
            value.append(v['Value'])
    return value


def try_record(test, record):
    """Return a value for a record"""
    """Return a value for a record"""
    return record.get(test, '')


def write_zone_to_csv(zone, zone_records):
    """Write hosted zone records to a csv file in /tmp/."""
    zone_file_name = '/tmp/' + zone['Name'] + '.csv'
    fieldnames = [
        'NAME', 'TYPE', 'VALUE',
        'TTL', 'REGION', 'WEIGHT',
        'SETID', 'FAILOVER', 'EVALUATE_HEALTH'
    ]
    with open(zone_file_name, 'w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in zone_records:
            values = get_record_value(record)
            for value in values:
                writer.writerow({
                    'NAME': record['Name'],
                    'TYPE': record['Type'],
                    'VALUE': value,
                    'TTL': try_record('TTL', record),
                    'REGION': try_record('Region', record),
                    'WEIGHT': try_record('Weight', record),
                    'SETID': try_record('SetIdentifier', record),
                    'FAILOVER': try_record('Failover', record),
                    'EVALUATE_HEALTH': try_record(
                        'EvaluateTargetHealth', try_record('AliasTarget', record)
                    )
                })
    return zone_file_name


def write_zone_to_json(zone, zone_records):
    """Write hosted zone records to a json file in /tmp/."""
    # create the file name
    zone_file_name = '/tmp/' + zone['Name'] + '.json'
    try:
        # use context manager to write the records to the file
        with open(zone_file_name, 'w') as json_file:
            json.dump(zone_records, json_file, indent=4)
    except Exception as e:
        print(f"Error writing to file: {e}")
        return None
    return zone_file_name


## HANDLER FUNCTION ##

def lambda_handler(event, context):
    """Handler function for AWS Lambda"""
    time_stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())

    hosted_zoned = get_route53_hosted_zones()
    for zone in hosted_zoned:
        zone_folder = (time_stamp + '/' + zone['Name'][:-1])
        zone_records = get_route53_zone_records(zone['Id'])
        upload_to_s3(
            zone_folder,
            write_zone_to_csv(zone, zone_records),
            s3_bucket_name,
            (zone['Name'] + 'csv')
        )
        upload_to_s3(
            zone_folder,
            write_zone_to_json(zone, zone_records),
            s3_bucket_name,
            (zone['Name'] + 'json')
        )
    return True


if __name__ == "__main__":
    lambda_handler(0, 0)
