# SPDX-License-Identifier: MPL-2.0
# Copyright 2021 John Mille<john@ews-network.net>

"""Main module."""

from __future__ import annotations

import re
from os import environ

from aws_cfn_custom_resource_resolve_parser import handle
from cfn_resource_provider import ResourceProvider
from cfn_resource_provider.resource_provider import is_int
from compose_x_common.compose_x_common import keypresent
from kafka import errors

from cfn_kafka_admin.common import setup_logging
from cfn_kafka_admin.kafka_resources.topics_management import (
    create_new_kafka_topic,
    delete_topic,
    update_kafka_topic,
)
from cfn_kafka_admin.models.admin import EwsKafkaTopic

LOG = setup_logging(__name__)

INT_RE = re.compile(r"(^[1-9]+\d*$|^0$)")
FLOAT_RE = re.compile(r"(^\d+\.\d+$|^\.\d+$)")


def is_float(number: str) -> bool:
    if len(number) > 0 and number[0] in ("-", "+"):
        match = FLOAT_RE.match(number[1:])
    else:
        match = FLOAT_RE.match(number)
    if not match:
        return False
    return True


class KafkaTopic(ResourceProvider):
    def __init__(self):
        """
        Init method
        """
        self.cluster_info = {}
        super().__init__()
        self.request_schema = EwsKafkaTopic.schema()

    def heuristic_convert_property_types(self, properties):
        """
        heuristic type conversion of string values in `properties`.
        """
        if isinstance(properties, dict):
            for name in properties:
                properties[name] = self.heuristic_convert_property_types(
                    properties[name]
                )
        elif isinstance(properties, list):
            for i, v in enumerate(properties):
                properties[i] = self.heuristic_convert_property_types(v)
        elif isinstance(properties, str):
            v = str(properties)
            if v == "true":
                return True
            elif v == "false":
                return False
            elif is_float(v):
                return float(v)
            elif is_int(v):
                return int(v)
            else:
                pass
        return properties

    def convert_property_types(self):
        self.heuristic_convert_property_types(self.properties)
        int_props = ["PartitionsCount", "ReplicationFactor"]
        boolean_props = ["IsConfluentKafka"]
        for prop in int_props:
            if keypresent(prop, self.properties) and isinstance(
                self.properties[prop], str
            ):
                try:
                    self.properties[prop] = int(self.properties[prop])
                except Exception as error:
                    self.fail(
                        f"Failed to get cluster information - {prop} - {str(error)}"
                    )
        for prop in boolean_props:
            if keypresent(prop, self.properties) and isinstance(
                self.properties[prop], str
            ):
                self.properties[prop] = self.properties[prop].lower() == "true"

    def define_cluster_info(self):
        """
        Method to define the cluster information into a simple format
        """
        try:
            self.cluster_info["bootstrap_servers"] = self.get("BootstrapServers")
            self.cluster_info["security_protocol"] = self.get("SecurityProtocol")
            self.cluster_info["sasl_mechanism"] = self.get("SASLMechanism")
            self.cluster_info["sasl_plain_username"] = self.get("SASLUsername")
            self.cluster_info["sasl_plain_password"] = self.get("SASLPassword")
        except Exception as error:
            self.fail(f"Failed to get cluster information - {str(error)}")

        for key, value in self.cluster_info.items():
            if isinstance(value, str) and value.find("resolve:secretsmanager") >= 0:
                try:
                    self.cluster_info[key] = handle(value)
                except Exception as error:
                    LOG.error("Failed to import secrets from SecretsManager")
                    self.fail(str(error))

    def create(self):
        """
        Method to create a new Kafka topic
        :return:
        """
        try:
            LOG.info(f"Attempting to create new topic {self.get('Name')}")
            self.define_cluster_info()
            cluster_url = (
                self.cluster_info["bootstrap.servers"]
                if self.get("IsConfluentKafka")
                else self.cluster_info["bootstrap_servers"]
            )
            LOG.info(f"Cluster is {cluster_url}")
        except Exception as error:
            self.fail(f"Failed to initialize - {str(error)}")
        if not self.get("PartitionsCount") >= 1:
            self.fail("The number of partitions must be a strictly positive value >= 1")
        try:
            LOG.info(f'{self.get("Name")} - {self.get("Settings")}')
            topic_name = create_new_kafka_topic(
                self.get("Name"),
                self.get("PartitionsCount"),
                self.cluster_info,
                replication_factor=self.get("ReplicationFactor"),
                settings=self.get("Settings"),
            )
            self.physical_resource_id = topic_name
            self.set_attribute("Name", self.get("Name"))
            self.set_attribute("Partitions", self.get("PartitionsCount"))
            self.set_attribute("BootstrapServers", self.get("BootstrapServers"))
            self.success(f"Created new topic {topic_name}")
        except errors.TopicAlreadyExistsError as error:
            if environ.get("FAIL_IF_ALREADY_EXISTS", None) is None:
                LOG.info(f"{self.get('Name')} - Importing existing Topic")
                self.physical_resource_id = self.get("Name")
                self.set_attribute("Name", self.get("Name"))
                self.set_attribute("Partitions", self.get("PartitionsCount"))
                self.set_attribute("BootstrapServers", self.get("BootstrapServers"))
                self.success("Existing topic imported")
            else:
                self.physical_resource_id = "could-not-create-nor-import"
                self.fail(
                    f"{self.get('Name')} - Topic already exists and import is disabled, {str(error)}"
                )
        except Exception as error:
            LOG.exception(error)
            self.physical_resource_id = "could-not-create"
            self.fail(f"Failed to create the topic {self.get('Name')}, {str(error)}")

    def update(self):
        """
        :return:
        """
        try:
            self.define_cluster_info()
            update_kafka_topic(
                self.get("Name"),
                self.get("PartitionsCount"),
                self.cluster_info,
                settings=self.get("Settings"),
            )
            self.physical_resource_id = self.get("Name")
            self.set_attribute("Name", self.get("Name"))
            self.set_attribute("Partitions", self.get("PartitionsCount"))
            self.set_attribute("BootstrapServers", self.get("BootstrapServers"))
            self.success(
                reason="Topic {} successfully updated.".format(self.get("Name"))
            )
        except Exception as error:
            self.fail(str(error))

    def delete(self):
        """
        Method to delete the Topic resource
        :return:
        """
        LOG.info("Delet: topic attribute name: {}".format(self.get("Name")))
        if self.get("Name") is None or (
            self.physical_resource_id
            and re.match(r"(.*)could-not-create(.*)$", self.physical_resource_id)
        ):
            LOG.warning("Deleting failed create resource.")
            self.success("Deleting non-working resource")
            return
        try:
            self.define_cluster_info()
            delete_topic(self.get("Name"), self.cluster_info)
        except errors.UnknownTopicOrPartitionError:
            self.success(
                f"Topic {self.get_attribute('Name')} does not exist. Nothing to delete."
            )
        except Exception as error:
            LOG.exception(error)
            if environ.get("DELETE_FAIL_ON_ERROR", None) is None:
                self.success(
                    f"Failed to delete topic. But ignoring failure {self.get_attribute('Name')}. {str(error)}"
                )
            else:
                self.fail(
                    f"Failed to delete topic {self.get_attribute('Name')}. {str(error)}"
                )


def lambda_handler(event, context):
    """
    AWS Lambda Function handler for topics management

    :param dict event:
    :param dict context:
    """
    provider = KafkaTopic()
    provider.handle(event, context)


if __name__ == "__main__":
    print(KafkaTopic().request_schema)
