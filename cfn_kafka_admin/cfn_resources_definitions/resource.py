#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2020-2021 John Mille <john@ews-network.net>

"""Definition of EWS::Kafka::Topic resource."""

from troposphere import AWSObject
from troposphere.validators import positive_integer

from cfn_kafka_admin.cfn_resources_definitions import KafkaAclPolicy


class KafkaTopic(AWSObject):
    """
    Class to represent EWS::Kafka::Topic
    """

    resource_type = "EWS::Kafka::Topic"
    props = {
        "BootstrapServers": (str, True),
        "ReplicationFactor": (positive_integer, False),
        "SecurityProtocol": (str, False),
        "SASLMechanism": (str, False),
        "SASLUsername": (str, False),
        "SASLPassword": (str, False),
        "Name": (str, True),
        "PartitionsCount": (positive_integer, True),
        "Settings": (dict, False),
    }


class KafkaAcl(AWSObject):
    """
    Class to represent EWS::Kafka::ACL
    """

    resource_type = "EWS::Kafka::ACL"
    props = {
        "BootstrapServers": (str, True),
        "ReplicationFactor": (positive_integer, False),
        "SecurityProtocol": (str, False),
        "SASLMechanism": (str, False),
        "SASLUsername": (str, False),
        "SASLPassword": (str, False),
        "Policies": ([KafkaAclPolicy], True),
    }


class KafkaTopicSchema(AWSObject):
    """
    Class to represent EWS::Kafka::Schema
    """

    resource_type = "EWS::Kafka::Schema"
    props = {
        "RegistryUrl": (str, True),
        "RegistryUsername": (str, False),
        "RegistryPassword": (str, False),
        "RegistryUserInfo": (str, False),
        "Subject": (str, True),
        "Type": (str, True),
        "Definition": ((str, dict), True),
        "SerializeAttribute": (str, True),
        "CompatibilityMode": (str, True),
    }
