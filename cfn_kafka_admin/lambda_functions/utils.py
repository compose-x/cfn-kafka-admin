#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2020-2021 John Mille <john@compose-x.io>

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cfn_resource_provider import ResourceProvider

import logging

from aws_cfn_custom_resource_resolve_parser import handle

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


def cfn_resolve_string(cfn_resource: ResourceProvider):
    for key, value in cfn_resource.cluster_info.items():
        if isinstance(value, str) and value.find("resolve:secretsmanager") >= 0:
            try:
                cfn_resource.cluster_info[key] = handle(value)
            except Exception as error:
                LOG.error("Failed to import secrets from SecretsManager")
                cfn_resource.fail(str(error))


def define_cluster_info(cfn_resource: ResourceProvider):
    """Function to define the cluster information into Confluent python client format"""
    try:
        cfn_resource.cluster_info["bootstrap.servers"] = cfn_resource.get(
            "BootstrapServers"
        )
        cfn_resource.cluster_info["security.protocol"] = cfn_resource.get(
            "SecurityProtocol"
        )
        cfn_resource.cluster_info["sasl.mechanism"] = cfn_resource.get("SASLMechanism")
        cfn_resource.cluster_info["sasl.username"] = cfn_resource.get("SASLUsername")
        cfn_resource.cluster_info["sasl.password"] = cfn_resource.get("SASLPassword")
    except Exception as error:
        cfn_resource.fail(f"Failed to get cluster information - {str(error)}")

    cfn_resolve_string(cfn_resource)


def set_client_info(cfn_resource: ResourceProvider):
    """Function to set the client information"""
    client_config = cfn_resource.get("ClientConfig", {})
    if not client_config:
        try:
            define_cluster_info(cfn_resource)
        except Exception as error:
            cfn_resource.fail(str(error))
    else:
        cfn_resource.cluster_info = client_config
    try:
        cfn_resolve_string(cfn_resource)
    except Exception as error:
        cfn_resource.fail(str(error))
