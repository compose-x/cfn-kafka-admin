#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2020-2021 John Mille <john@ews-network.net>


"""Main module."""

import json
import re
from copy import deepcopy
from datetime import datetime as dt
from uuid import uuid4

import boto3
import yaml
from compose_x_common.compose_x_common import keyisset, keypresent, set_else_none

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from troposphere import AWS_NO_VALUE, GetAtt, Ref, Sub, Template

from cfn_kafka_admin.models.admin import *

DATE = dt.utcnow().isoformat()
FILE_PREFIX = f'{dt.utcnow().strftime("%Y/%m/%d/%H%M")}/{str(uuid4().hex)[:6]}/'

from .cfn_resources_definitions import KafkaAclPolicy
from .cfn_resources_definitions.custom import KafkaAcl as CACLs
from .cfn_resources_definitions.custom import KafkaTopic as CTopic
from .cfn_resources_definitions.custom import KafkaTopicSchema as CTopicSchema
from .cfn_resources_definitions.resource import KafkaAcl as RACLs
from .cfn_resources_definitions.resource import KafkaTopic as RTopic
from .cfn_resources_definitions.resource import KafkaTopicSchema as RTopicSchema

NONALPHANUM = re.compile(r"([^a-zA-Z0-9]+)")


def merge_topics(final, override, extend_config_only=False):
    """
    Function to override and update new_settings from override to primary
    Topics are filtered out via the Name property
    :param dict final:
    :param dict override:
    :param extend_config_only: Whether the policies or ACLs can be merged.
    :return: The final merged dict
    :rtype: dict
    """
    if keyisset("Topics", override):
        override_top_topics = Topics.parse_obj(override["Topics"]).dict(
            by_alias=True,
        )
        if extend_config_only:
            # Allows to add the config and ensure that we do not import topics from config
            if keypresent("Topics", override_top_topics):
                del override_top_topics["Topics"]
            final["Topics"].update(override_top_topics)
        elif not extend_config_only and keyisset("Topics", override_top_topics):
            if keyisset("Topics", final["Topics"]):
                existing_topics = deepcopy(final["Topics"]["Topics"])
                override_topics = deepcopy(override_top_topics["Topics"])
                merged_lists = override_topics + existing_topics
                del final["Topics"]["Topics"]
                del override_top_topics["Topics"]
                topics = list({v["Name"]: v for v in merged_lists}.values())
                final["Topics"].update(override_top_topics)
                final["Topics"]["Topics"] = topics
            elif not keypresent("Topics", final["Topics"]):
                override_topics = deepcopy(override_top_topics["Topics"])
                del override_top_topics["Topics"]
                topics = list({v["Name"]: v for v in override_topics}.values())
                final["Topics"].update(override_top_topics)
                final["Topics"]["Topics"] = topics


def merge_acls(final, override, extend_all=False):
    """
    Function to override and update new_settings from override to primary
    All ACL policy is a dictionary made of simple objects, no key filtering

    :param dict final:
    :param dict override:
    :param extend_all: Whether the policies or ACLs can be merged.
    :return: The final merged dict
    :rtype: dict
    """
    if keyisset("ACLs", override):
        override_acls = ACLs.parse_obj(override["ACLs"]).dict(by_alias=True)
        if keypresent("Policies", override_acls) and not extend_all:
            del override_acls["Policies"]
            final["ACLs"].update(override_acls)
        elif keyisset("Policies", override_acls) and extend_all:
            if keyisset("Policies", final["ACLs"]):
                merged_lists = override_acls["Policies"] + final["ACLs"]["Policies"]
            else:
                merged_lists = override_acls["Policies"]
            acls = [dict(y) for y in set(tuple(x.items()) for x in merged_lists)]
            final["ACLs"].update(override_acls)
            final["ACLs"]["Policies"] = acls


def merge_contents(primary, override, extend_all=False):
    """
    Function to override and update new_settings from override to primary
    :param primary:
    :param override:
    :param extend_all: Whether the policies or ACLs can be merged.
    :return: The final merged dict
    :rtype: dict
    """
    if not isinstance(override, dict):
        raise TypeError(
            "The content of the override file does not match the expected content pattern."
        )
    final = dict(deepcopy(primary))
    if (
        keypresent("Globals", final)
        and keyisset("Globals", override)
        and isinstance(override["Globals"], dict)
    ):
        override_globals = EwsKafkaParameters.parse_obj(override["Globals"])
        final["Globals"].update(override_globals.dict(by_alias=True))

    if (
        keypresent("Schemas", final)
        and keyisset("Schemas", override)
        and isinstance(override["Schemas"], dict)
    ):
        override_globals = Schemas.parse_obj(override["Schemas"])
        final["Schemas"].update(override_globals.dict(by_alias=True))
    elif (
        not keypresent("Schemas", final)
        and keyisset("Schemas", override)
        and isinstance(override["Schemas"], dict)
    ):
        override_globals = Schemas.parse_obj(override["Schemas"])
        final["Schemas"] = override_globals.dict(by_alias=True)

    merge_acls(final, override, extend_all)
    merge_topics(final, override, not extend_all)
    return final


class KafkaStack(object):
    """
    Class to represent the Kafka topics / acls / schemas in CloudFormation.
    """

    def __init__(self, files_paths, config_file_path=None):
        self.model = None
        self.template = Template("Kafka topics-acls-schemas root")
        self.stack = None
        self.topic_class = RTopic
        self.acl_class = RACLs
        self.schemas_r = {}
        self.topics_r = {}
        self.globals_config = {}
        final_content = {"Globals": {}, "Topics": {}, "ACLs": {}}
        for file_path in files_paths:
            if file_path.endswith(".yaml") or file_path.endswith(".yml"):
                with open(file_path, "r") as file_fd:
                    file_content = file_fd.read()
                yaml_content = yaml.load(file_content, Loader=Loader)
                final_content = merge_contents(
                    final_content, yaml_content, extend_all=True
                )
        if config_file_path:
            with open(config_file_path, "r") as override_fd:
                override_content = override_fd.read()
            override_content = yaml.load(override_content, Loader=Loader)
            final_content = merge_contents(final_content, override_content)
            print("FINAL", type(final_content), final_content.keys())
            for topic in final_content["Topics"]["Topics"]:
                if keyisset("Settings", topic):
                    settingss = TopicsSettings().parse_obj(topic["Settings"])
                    print("SETTINGS DEFINED?", settingss, settingss.dict(by_alias=True))
                    topic["Settings"] = (
                        TopicsSettings()
                        .parse_obj(topic["Settings"])
                        .dict(
                            by_alias=True,
                            exclude_none=True,
                            exclude_unset=True,
                            exclude_defaults=True,
                        )
                    )
                    print("TOPIC", topic["Name"], "NEW SETTINGS", topic["Settings"])

        self.model = Model.parse_obj(final_content)

        if not self.model.Topics and not self.model.ACLs:
            raise KeyError("You must define at least one of ACLs or Topics")
        self.set_globals()

    def set_globals(self):
        """
        Method to set the global new_settings
        """
        self.globals_config.update(
            {
                "BootstrapServers": self.model.Globals.BootstrapServers.__root__,
                "SASLUsername": self.model.Globals.SASLUsername.__root__
                if self.model.Globals.SASLUsername.__root__
                else Ref(AWS_NO_VALUE),
                "SASLPassword": self.model.Globals.SASLPassword.__root__
                if self.model.Globals.SASLPassword.__root__
                else Ref(AWS_NO_VALUE),
                "SASLMechanism": SASLMechanism[
                    self.model.Globals.SASLMechanism.name
                ].value
                if isinstance(self.model.Globals.SASLMechanism, SASLMechanism)
                else self.model.Globals.SASLMechanism,
                "SecurityProtocol": SecurityProtocol[
                    self.model.Globals.SecurityProtocol.name
                ].value
                if isinstance(self.model.Globals.SecurityProtocol, SecurityProtocol)
                else self.model.Globals.SecurityProtocol,
            }
        )

    def define_schema_definition_path(
        self, topic_name: str, subject_suffix: str, attribute: TopicSchemaDef
    ):
        file_name = None
        if isinstance(attribute.Definition, str):
            try:
                with open(attribute.Definition, "r") as definition_fd:
                    file_name = attribute.Definition
                    definition = json.dumps(json.loads(definition_fd.read()))
            except FileNotFoundError:
                print("Failed to load file, using string literal as definition")
                definition = attribute.Definition
        else:
            definition = attribute.Definition
            file_name = f"{topic_name}{SerializerDef[attribute.Serializer.name].value}{subject_suffix}Schema.json"

        if self.model.Schemas.S3Store and file_name:
            s3_file_path = (
                f"{self.model.Schemas.S3Store.PrefixPath}{FILE_PREFIX}{file_name}"
            )
            session = boto3.session.Session()
            resource = session.resource("s3")
            bucket = resource.Bucket(self.model.Schemas.S3Store.BucketName)
            s3_file = bucket.Object(key=s3_file_path)
            s3_file.put(Body=definition, ContentType="application/json")
            s3_uri = f"s3://{s3_file.bucket_name}/{s3_file.key}"
            print(f"Uploaded schema {file_name} to {s3_uri}")
            return s3_uri
        else:
            return definition

    def add_attribute_schema(
        self,
        topic_name: str,
        registry_url,
        registry_username,
        registry_password,
        registry_userinfo,
        schema_class,
        attribute: TopicSchemaDef,
        subject_suffix: str,
        deletion_policy,
    ):

        definition = self.define_schema_definition_path(
            topic_name, subject_suffix, attribute
        )
        topic_schema_r = schema_class(
            f"{topic_name}{SerializerDef[attribute.Serializer.name].value}{subject_suffix}Schema",
            DeletionPolicy=deletion_policy,
            SerializeAttribute=subject_suffix,
            Serializer=SerializerDef[attribute.Serializer.name].value,
            Definition=definition,
            Subject=Sub(f"${{{topic_name}.Name}}-{subject_suffix}"),
            RegistryUrl=registry_url,
            RegistryUsername=registry_username
            if isinstance(registry_username, Ref)
            else registry_username.__root__,
            RegistryPassword=registry_password
            if isinstance(registry_password, Ref)
            else registry_password.__root__,
            RegistryUserInfo=registry_userinfo.__root__,
            CompatibilityMode=CompatibilityMode[attribute.CompatibilityMode.name].value,
        )
        if schema_class is CTopicSchema:
            function_name = (
                self.model
                if self.model.Schemas.FunctionName.startswith("arn:aws")
                else Sub(
                    "arn:${AWS::Partition}:lambda:${AWS::Region}:${AWS::AccountId}:function:"
                    f"{self.model.Schemas.FunctionName}"
                )
            )
            setattr(topic_schema_r, "ServiceToken", function_name)
        self.schemas_r[topic_name] = topic_schema_r
        self.template.add_resource(topic_schema_r)

    def add_topic_schema(self, topic_name, schema_definition):
        """
        Method to create a new schema for the given topic

        :param str topic_name:
        :param Schema schema_definition:
        """
        schema_class = RTopicSchema
        if self.model.Schemas and self.model.Schemas.FunctionName:
            schema_class = CTopicSchema
        schema_config = schema_definition.dict()

        if self.model.Schemas and self.model.Schemas.RegistryUrl:
            registry_url = self.model.Schemas.RegistryUrl
        elif keyisset("RegistryUrl", schema_config):
            registry_url = schema_config["RegistryUrl"]
        else:
            raise KeyError(
                "RegistryUrl is not defined in Schema new_settings nor in Schemas"
            )

        if self.model.Schemas and self.model.Schemas.RegistryUsername:
            registry_username = self.model.Schemas.RegistryUsername
        elif keyisset("RegistryUsername", schema_config):
            registry_username = schema_config["RegistryUsername"]
        else:
            registry_username = Ref(AWS_NO_VALUE)

        if self.model.Schemas and self.model.Schemas.RegistryPassword:
            registry_password = self.model.Schemas.RegistryPassword
        elif keyisset("RegistryPassword", schema_config):
            registry_password = schema_config["RegistryPassword"]
        else:
            registry_password = Ref(AWS_NO_VALUE)

        if self.model.Schemas and self.model.Schemas.RegistryUserInfo:
            registry_userinfo = self.model.Schemas.RegistryUserInfo
        elif keyisset("RegistryUserInfo", schema_config):
            registry_userinfo = schema_config["RegistryUserInfo"]
        else:
            registry_userinfo = Ref(AWS_NO_VALUE)

        if keyisset("DeletionPolicy", schema_config):
            deletion_policy = DeletionPolicy[schema_config["DeletionPolicy"].name].value
            if (
                self.model.Schemas
                and self.model.Schemas.DeletionPolicy
                and DeletionPolicy[self.model.Schemas.DeletionPolicy.name].value
                != deletion_policy
            ):
                print(
                    f"WARNING !_! Schema for topic {topic_name} overrides global "
                    f"{DeletionPolicy[self.model.Schemas.DeletionPolicy.name].value} policy with {deletion_policy}"
                )
        elif self.model.Schemas and self.model.Schemas.DeletionPolicy:
            deletion_policy = DeletionPolicy[
                self.model.Schemas.DeletionPolicy.name
            ].value
        else:
            deletion_policy = "Retain"

        if registry_userinfo and not isinstance(registry_userinfo, Ref):
            registry_username = Ref(AWS_NO_VALUE)
            registry_password = Ref(AWS_NO_VALUE)

        if schema_definition.Key:
            self.add_attribute_schema(
                topic_name,
                registry_url,
                registry_username,
                registry_password,
                registry_userinfo,
                schema_class,
                schema_definition.Key,
                "key",
                deletion_policy,
            )
        if schema_definition.Value:
            self.add_attribute_schema(
                topic_name,
                registry_url,
                registry_username,
                registry_password,
                registry_userinfo,
                schema_class,
                schema_definition.Value,
                "value",
                deletion_policy,
            )

    def render_topics(self):
        if not self.model.Topics or not self.model.Topics.Topics:
            return
        function_name = None
        if self.model.Topics.FunctionName:
            self.topic_class = CTopic
            function_name = (
                function_name
                if self.model.Topics.FunctionName.startswith("arn:aws")
                else Sub(
                    "arn:${AWS::Partition}:lambda:${AWS::Region}:${AWS::AccountId}:function:"
                    f"{self.model.Topics.FunctionName}"
                )
            )
        for topic in self.model.Topics.Topics:
            topic_cfg = topic.dict()
            if function_name:
                topic_cfg.update({"ServiceToken": function_name})
            topic_cfg.update(self.globals_config)
            topic_cfg.update(
                {
                    "ReplicationFactor": self.model.Topics.ReplicationFactor.__root__
                    if not topic.ReplicationFactor
                    else topic.ReplicationFactor,
                }
            )
            if keypresent("Settings", topic_cfg) and not keyisset(
                "Settings", topic_cfg
            ):
                del topic_cfg["Settings"]
            else:
                topic_cfg["Settings"] = json.loads(
                    topic.Settings.json(
                        by_alias=True,
                        exclude_none=True,
                        exclude_unset=True,
                        exclude_defaults=True,
                    )
                )
            topic_title_raw = topic.Name.__root__
            topic_title = topic_title_raw.replace("-", "").title()
            topic_title = NONALPHANUM.sub("", topic_title)

            if topic.Schema and keyisset("Schema", topic_cfg):
                self.add_topic_schema(topic_title, topic.Schema)
                del topic_cfg["Schema"]
            if keypresent("Schema", topic_cfg):
                del topic_cfg["Schema"]
            topic_r = self.template.add_resource(
                self.topic_class(
                    topic_title,
                    DeletionPolicy=DeletionPolicy[
                        self.model.Topics.DeletionPolicy.name
                    ].value,
                    **topic_cfg,
                )
            )
            self.topics_r[topic.Name.__root__] = topic_r

    def import_topic_name(self, policy):
        """
        Method to identify whether the resource provided is a topic referenced in the template

        :param Policy policy:
        :return:
        """
        if policy.ResourceType.value == ResourceType.TOPIC.name:
            topic_name = policy.Resource
            if topic_name in self.topics_r.keys():
                return GetAtt(self.topics_r[policy.Resource], "Name")
        return policy.Resource

    def render_acls(self):
        if not self.model.ACLs or not self.model.ACLs.Policies:
            return
        function_name = None
        if self.model.ACLs.FunctionName:
            self.acl_class = CACLs
            function_name = (
                function_name
                if self.model.ACLs.FunctionName.startswith("arn:aws")
                else Sub(
                    "arn:${AWS::Partition}:lambda:${AWS::Region}:${AWS::AccountId}:function:"
                    f"{self.model.ACLs.FunctionName}"
                )
            )
        acl = {}
        acl.update(self.globals_config)
        if function_name:
            acl.update({"ServiceToken": function_name})

        policies = []
        for policy in self.model.ACLs.Policies.__root__:
            if isinstance(policy.PatternType, str):
                pattern_key = policy.PatternType
            else:
                pattern_key = policy.PatternType.name
            policies.append(
                KafkaAclPolicy(
                    Resource=self.import_topic_name(policy),
                    ResourceType=ResourceType[policy.ResourceType.name].value,
                    Principal=policy.Principal,
                    PatternType=PatternType[pattern_key].value,
                    Action=Action[policy.Action.name].value,
                    Effect=Effect[policy.Effect.name].value,
                    Host=policy.Host if policy.Host else r"*",
                )
            )
        self.template.add_resource(
            self.acl_class("ACLs", DeletionPolicy="Retain", Policies=policies, **acl)
        )
