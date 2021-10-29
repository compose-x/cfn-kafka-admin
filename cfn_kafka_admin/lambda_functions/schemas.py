#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2021 John Mille<john@ews-network.net>

"""Module to handle the custom resource for Schemas"""

import logging

from aws_cfn_custom_resource_resolve_parser import handle
from cfn_resource_provider import ResourceProvider
from kafka_schema_registry_admin.kafka_schema_registry_admin import SchemaRegistry

from cfn_kafka_admin.models.admin import EwsKafkaSchema

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


class KafkaSchema(ResourceProvider):
    def __init__(self):
        """
        Init method
        """
        self.cluster_info = {}
        super(KafkaSchema, self).__init__()
        self.request_schema = EwsKafkaSchema.schema()

    def try_replace_from_secret(self, param):
        if (
            isinstance(self.get(param), str)
            and self.get(param).find("resolve:secretsmanager") >= 0
        ):
            try:
                return handle(self.get(param))
            except Exception as error:
                LOG.error("Failed to import secrets from SecretsManager")
                self.fail(str(error))
        else:
            return self.get(param)

    def set_registry(self):
        if self.get("RegistryUserInfo"):
            user_info = self.try_replace_from_secret("RegistryUserInfo")
            username = user_info.split(":")[0]
            password = user_info.split(":")[1]
        else:
            username = self.try_replace_from_secret("RegistryUsername")
            password = self.try_replace_from_secret("RegistryPassword")
        registry_url = self.try_replace_from_secret("RegistryUrl")
        LOG.info(registry_url)
        registry = SchemaRegistry(
            **{
                "SchemaRegistryUrl": registry_url,
                "Username": username,
                "Password": password,
            }
        )
        return registry

    def create(self):
        """
        Creates a new Schema / Version in the Schema Registry
        """
        try:
            registry = self.set_registry()
            subject = self.get("Subject")
            serializer = self.get("Serializer")
            compatibility = self.get("CompatibilityMode")
            schema_def = self.get("Definition")
            schema = registry.post_subject_version(
                subject, schema_def, schema_type=serializer
            )
            registry.put_compatibility_subject_config(
                subject_name=subject, compatibility=compatibility
            )
            self.set_attribute("Id", schema["id"])
            self.physical_resource_id = subject
            self.success("Schema version created")
        except Exception as error:
            self.physical_resource_id = "could-not-create"
            self.fail(str(error))

    def update(self):
        """
        Updates the schema definition to create a new version. First, checks that the new definition is compatible.
        """
        try:
            registry = self.set_registry()
            subject = self.get("Subject")
            serializer = self.get("Serializer")
            schema_def = self.get("Definition")
            compatible = registry.post_compatibility_subjects_versions(
                subject_name=subject,
                version_id="latest",
                definition=schema_def,
                definition_type=serializer,
                as_bool=True,
            )
            if not compatible:
                print(schema_def)
                self.fail(
                    f"Schema for {subject} is not compatible with the latest version"
                )
            schema = registry.post_subject_version(subject, schema_def)
            self.set_attribute("Id", schema["id"])
            self.success("New schema version created")
        except Exception as error:
            self.fail(str(error))

    def delete(self):
        """
        Deletes the schema subject from the registry
        """
        LOG.info(self.get("Id"))
        LOG.info(self.physical_resource_id)
        if (
            self.get("Id") is None
            and self.physical_resource_id
            and self.physical_resource_id.startswith("could-not-create")
        ):
            LOG.warning("Deleting failed create resource. Nothing to do")
            self.success("Deleting failed create resource. Nothing to do")
            return
        try:
            registry = self.set_registry()
            subject = self.get("Subject")
            registry.delete_subject(subject, permanent=False)
            self.success("Schema successfully deleted")
        except Exception as error:
            self.fail(str(error))


def lambda_handler(event, context):
    provider = KafkaSchema()
    provider.handle(event, context)


if __name__ == "__main__":
    print(KafkaSchema().request_schema)
