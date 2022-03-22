#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2021 John Mille<john@ews-network.net>

"""Module to handle the custom resource for Schemas"""

import json
import logging
import re

from aws_cfn_custom_resource_resolve_parser import handle
from boto3.session import Session
from cfn_resource_provider import ResourceProvider
from kafka_schema_registry_admin.kafka_schema_registry_admin import SchemaRegistry

from cfn_kafka_admin.models.admin import EwsKafkaSchema

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


def pull_from_s3(s3_uri: str) -> str:
    """
    Function to pull the definition from S3 and return the JSON String
    :param s3_uri:
    :return: The definition
    """
    bucket_re = re.compile(r"s3://(?P<bucket>[a-z0-9-.]+)/(?P<key>[\S]+$)")
    parts = bucket_re.match(s3_uri)
    if not parts:
        raise ValueError(
            "The S3 URI is not valid", s3_uri, "Must match", bucket_re.pattern
        )
    bucket_name = parts.group("bucket")
    key = parts.group("key")
    session = Session()
    s3_resource = session.resource("s3")
    schema_s3_obj = s3_resource.Object(bucket_name, key)
    body = schema_s3_obj.get()["Body"].read().decode("utf-8")
    try:
        body_obj = json.loads(body)
        LOG.info(f"Successfully retrieved schema from {s3_uri}{schema_s3_obj.e_tag}")
        return json.dumps(body_obj)
    except Exception as error:
        LOG.exception(error)
        raise


def import_definition(schema_definition: str) -> str:
    """
    Checks whether the definition is a S3 URI or not. If yes, tries to pull from S3.
    """
    if schema_definition.startswith(r"s3://"):
        LOG.info(f"Attempting to retrieve file from S3 {schema_definition}")
        return pull_from_s3(schema_definition)
    else:
        LOG.info("Using definition as-is.")
        return schema_definition


class KafkaSchema(ResourceProvider):
    """
    Class for custom resource to handle a Kafka Schema
    """

    def __init__(self):
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
            schema_def = import_definition(self.get("Definition"))
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
            LOG.exception(error)
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
            schema_def = import_definition(self.get("Definition"))
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
            LOG.exception(error)
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
