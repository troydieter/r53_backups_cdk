"""AWS Route 53 Lambda Backup"""

import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

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
def upload_to_s3(folder: str, filename: Path, bucket_name: str, key: str) -> None:
    """Upload a file to a folder in an Amazon S3 bucket."""
    if not filename.exists():
        raise FileNotFoundError(f"{filename} does not exist.")

    key = folder + "/" + key
    try:
        s3.upload_file(str(filename), bucket_name, key)
        print(f"Uploaded {filename} to {bucket_name}/{key}")
    except Exception as e:
        raise Exception(f"Failed to upload {filename} to S3 bucket {bucket_name} due to {e}")


def get_route53_hosted_zones(next_zone=None):
    """Recursively returns a list of hosted zones in Amazon Route 53."""
    if next_zone:
        response = route53.list_hosted_zones_by_name(
            DNSName=next_zone[0],
            HostedZoneId=next_zone[1]
        )
    else:
        response = route53.list_hosted_zones_by_name()
    hosted_zones = response['HostedZones']
    # if response is truncated, call function again with next zone name/id
    if response['IsTruncated']:
        hosted_zones += get_route53_hosted_zones(
            (response['NextDNSName'],
             response['NextHostedZoneId'])
        )
    return hosted_zones


def get_route53_zone_records(zone_id, next_record=None):
    """Recursively returns a list of records of a hosted zone in Route 53."""
    if next_record:
        response = route53.list_resource_record_sets(
            HostedZoneId=zone_id,
            StartRecordName=next_record[0],
            StartRecordType=next_record[1]
        )
    else:
        response = route53.list_resource_record_sets(HostedZoneId=zone_id)
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
    # test for Key and Type errors
    try:
        value = record[test]
    except KeyError:
        value = ''
    except TypeError:
        value = ''
    return value


def write_zone_to_csv(zone, zone_records):
    """Write hosted zone records to a csv file in /tmp/."""
    zone_file_name = '/tmp/' + zone['Name'] + 'csv'
    # write to csv file with zone name
    with open(zone_file_name, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        # write column headers
        writer.writerow([
            'NAME', 'TYPE', 'VALUE',
            'TTL', 'REGION', 'WEIGHT',
            'SETID', 'FAILOVER', 'EVALUATE_HEALTH'
        ])
        # loop through all the records for a given zone
        for record in zone_records:
            csv_row = [''] * 9
            csv_row[0] = record['Name']
            csv_row[1] = record['Type']
            csv_row[3] = try_record('TTL', record)
            csv_row[4] = try_record('Region', record)
            csv_row[5] = try_record('Weight', record)
            csv_row[6] = try_record('SetIdentifier', record)
            csv_row[7] = try_record('Failover', record)
            csv_row[8] = try_record('EvaluateTargetHealth',
                                    try_record('AliasTarget', record)
                                    )
            value = get_record_value(record)
            # if multiple values (e.g., MX records), write each as its own row
            for v in value:
                csv_row[2] = v
                writer.writerow(csv_row)
    return zone_file_name


def write_zone_to_json(zone, zone_records):
    """Write hosted zone records to a json file in /tmp/."""
    zone_file_name = '/tmp/' + zone['Name'] + 'json'
    # write to json file with zone name
    with open(zone_file_name, 'w') as json_file:
        json.dump(zone_records, json_file, indent=4)
    return zone_file_name


## HANDLER FUNCTION ##

def lambda_handler(event, context):
    """Handler function for AWS Lambda"""
    time_stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                               datetime.utcnow().utctimetuple()
                               )

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
