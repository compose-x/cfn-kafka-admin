#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2021 John Mille<john@ews-network.net>

"""Main module."""
import uuid

from aws_cfn_custom_resource_resolve_parser import handle
from cfn_resource_provider import ResourceProvider
from compose_x_common.compose_x_common import keyisset, keypresent

from cfn_kafka_admin.common import setup_logging
from cfn_kafka_admin.kafka.acls_management import (
    create_new_acls,
    delete_acls,
    differentiate_old_new_acls,
)
from cfn_kafka_admin.models.admin import EwsKafkaAcl

LOG = setup_logging()


class KafkaACL(ResourceProvider):
    def __init__(self):
        """
        Init method
        """
        self.cluster_info = {}
        super(KafkaACL, self).__init__()
        self.request_schema = EwsKafkaAcl.schema()

    def convert_property_types(self):
        int_props = []
        boolean_props = []
        for prop in int_props:
            if keypresent(prop, self.properties) and isinstance(
                self.properties[prop], str
            ):
                self.properties[prop] = int(self.properties[prop])
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
            self.define_cluster_info()
            LOG.info(f"Connecting to {self.cluster_info['bootstrap_servers']}")
            LOG.info(f"Attempting to create new ACLs {self.get('Name')}")
            topic_name = create_new_acls(
                self.get("Policies"),
                self.cluster_info,
            )
            self.physical_resource_id = str(uuid.uuid4())
            self.set_attribute("Id", self.physical_resource_id)
            self.success(f"Created new ACLs {topic_name}")
        except Exception as error:
            self.physical_resource_id = "could-not-create"
            self.fail(f"Failed to create the ACLs. {str(error)}")

    def update(self):
        """
        :return:
        """
        try:
            self.define_cluster_info()
        except Exception as error:
            self.fail(str(error))
        old_policies = self.get_old("Policies")
        for policy in old_policies:
            if not keyisset("Host", policy):
                policy.update({"Host": "*"})
        new_policies = self.get("Policies")
        acls = differentiate_old_new_acls(new_policies, old_policies)
        LOG.info("ACLs deletion")
        LOG.info(acls[1])
        LOG.info("ACLs set")
        LOG.info(acls[0])
        try:
            delete_acls(acls[1], self.cluster_info)
        except Exception as error:
            LOG.error("Failed to delete old ACLs - Moving on")
            LOG.error(error)
            LOG.error(acls[1])
        try:
            create_new_acls(acls[0], self.cluster_info)
            self.success()
            LOG.info("Successfully created new ACLs")
        except Exception as error:
            LOG.error(error)
            LOG.error("Failed to create new ACLs")
            self.fail(str(error))

    def delete(self):
        """
        Method to delete the Topic resource
        :return:
        """
        try:
            self.define_cluster_info()
            delete_acls(self.get("Policies"), self.cluster_info)
            self.success("ACLs deleted")
        except Exception as error:
            self.fail(
                f"Failed to delete topic {self.get_attribute('Name')}. {str(error)}"
            )


def lambda_handler(event, context):
    provider = KafkaACL()
    provider.handle(event, context)


if __name__ == "__main__":
    print(KafkaACL().request_schema)
