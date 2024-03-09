#!/usr/bin/env python3
import aws_cdk as cdk

from infra.r53_stack import R53Stack

app = cdk.App()

props = {
    "namespace": app.node.try_get_context("namespace"),
    "schedule_minute": app.node.try_get_context("schedule_minute"),
    "schedule_hour": app.node.try_get_context("schedule_hour"),
    "schedule_week_day": app.node.try_get_context("schedule_week_day"),
    "schedule_month": app.node.try_get_context("schedule_month"),
    "schedule_year": app.node.try_get_context("schedule_year")
}

R53Stack(app, "R53BackupStack", props=props, description=f"Backup of {props['namespace']}-stack")

app.synth()
