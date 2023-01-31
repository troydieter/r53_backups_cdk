#!/usr/bin/env python3
import aws_cdk as cdk

from infra.r53_stack import R53Stack

app = cdk.App()

props = {
    "namespace": app.node.try_get_context("namespace")
}

R53Stack(app, "R53BackupStack", props=props, description=f"Backup of {props['namespace']}-stack")

app.synth()
