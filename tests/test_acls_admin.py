"""Tests ACLs creation, delete and update"""

import time
from os import path

from confluent_kafka.admin import (
    AclBinding,
    AclBindingFilter,
    AclOperation,
    AclPermissionType,
    ResourcePatternType,
    ResourceType,
)
from testcontainers.compose import DockerCompose

from cfn_kafka_admin.kafka_resources import get_admin_client
from cfn_kafka_admin.kafka_resources.acls import (
    create_new_acls,
    delete_acls,
    set_binding_filter_from_dict,
    set_binding_from_dict,
)

from ._common import get_connection_details


def list_acls(con_settings: dict):
    client = get_admin_client(con_settings, "ACLs", "LIST")
    _topics: dict = {}
    res = client.describe_acls(
        AclBindingFilter(
            ResourceType.ANY,
            name=None,
            resource_pattern_type=ResourcePatternType.ANY,
            principal=None,
            operation=AclOperation.ANY,
            permission_type=AclPermissionType.ANY,
            host=None,
        )
    )
    while not res.done():
        pass
    return res.result()


def test_create_acls(compose_path):
    with DockerCompose(
        path.abspath(compose_path),
        compose_file_name="docker-compose.yaml",
        wait=True,
        pull=True,
    ) as kafka:
        connection, sr_url = get_connection_details(kafka)
        cluster_settings = {"bootstrap.servers": connection}
        new_acls: list[dict] = [
            {
                "Resource": "topic-name",
                "PatternType": "LITERAL",
                "Principal": "User:toto",
                "ResourceType": "TOPIC",
                "Action": "ALL",
                "Effect": "ALLOW",
            },
            {
                "Resource": "my-consumer-group.",
                "PatternType": "PREFIXED",
                "Principal": "User:toto",
                "ResourceType": "GROUP",
                "Action": "READ",
                "Effect": "ALLOW",
            },
            {
                "Resource": "kafka-cluster",
                "PatternType": "LITERAL",
                "Principal": "User:toto",
                "ResourceType": "CLUSTER",
                "Action": "DESCRIBE_CONFIGS",
                "Effect": "ALLOW",
            },
            {
                "Resource": "kafka-cluster",
                "PatternType": "LITERAL",
                "Principal": "User:toto",
                "ResourceType": "BROKER",
                "Action": "DESCRIBE",
                "Effect": "ALLOW",
            },
            {
                "Resource": "kafka-cluster",
                "PatternType": "LITERAL",
                "Principal": "User:toto",
                "ResourceType": "TRANSACTIONAL_ID",
                "Action": "READ",
                "Effect": "ALLOW",
            },
        ]
        bindings: list[AclBinding] = [set_binding_from_dict(_acl) for _acl in new_acls]
        create_new_acls(
            new_acls,
            cluster_settings,
        )
        acls_list = list_acls(cluster_settings)
        print(acls_list)
        assert all(elem in bindings for elem in acls_list)


def test_create_delete_acls(compose_path):
    with DockerCompose(
        path.abspath(compose_path),
        compose_file_name="docker-compose.yaml",
        wait=True,
        pull=True,
    ) as kafka:
        connection, sr_url = get_connection_details(kafka)
        cluster_settings = {"bootstrap.servers": connection}
        new_acls: list[dict] = [
            {
                "Resource": "topic-name",
                "PatternType": "LITERAL",
                "Principal": "User:toto",
                "ResourceType": "TOPIC",
                "Action": "ALL",
                "Effect": "ALLOW",
            },
            {
                "Resource": "my-consumer-group.",
                "PatternType": "PREFIXED",
                "Principal": "User:toto",
                "ResourceType": "GROUP",
                "Action": "READ",
                "Effect": "ALLOW",
            },
        ]
        bindings: list[AclBinding] = [set_binding_from_dict(_acl) for _acl in new_acls]
        create_new_acls(
            new_acls,
            cluster_settings,
        )
        acls_list = list_acls(cluster_settings)
        print(acls_list)
        assert all(elem in bindings for elem in acls_list)
        deleted = delete_acls(new_acls, cluster_settings)
        assert all(_future.done() for _future in deleted.values())
        acls_list = list_acls(cluster_settings)
        print(acls_list)
        assert not acls_list
