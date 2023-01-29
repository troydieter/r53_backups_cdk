#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra.r53_stack import R53Stack

app = cdk.App()

props = {
    "namespace": app.node.try_get_context("namespace"),
    "hosted_zone_name": app.node.try_get_context("hosted_zone_name"),
    "hosted_zone_id": app.node.try_get_context("hosted_zone_id")
}

R53Stack(app, "R53BackupStack", props=props, description=f"Backup of {props['namespace']}-stack")

app.synth()
