"""Tests topics creation, delete and update"""

import os
from os import path

import pytest
from confluent_kafka import KafkaException
from testcontainers.compose import DockerCompose

from cfn_kafka_admin.kafka_resources import get_admin_client
from cfn_kafka_admin.kafka_resources.topics.create import create_new_kafka_topic
from cfn_kafka_admin.kafka_resources.topics.delete import delete_topic
from cfn_kafka_admin.kafka_resources.topics.update import update_kafka_topic

from ._common import get_connection_details


def list_topics(con_settings: dict):
    client = get_admin_client(con_settings, "LIST", "_all")
    _topics: dict = {}
    res = client.list_topics()
    for _topic in res.topics.values():
        print(_topic.topic, len(_topic.partitions))
    return res.topics


def test_create_topic(compose_path):
    with DockerCompose(
        path.abspath(compose_path),
        compose_file_name="docker-compose.yaml",
        wait=True,
        pull=True,
    ) as kafka:
        connection, sr_url = get_connection_details(kafka)
        cluster_settings = {"bootstrap.servers": connection}
        create_new_kafka_topic("dummy-no-settings", 1, cluster_settings, 1, {})
        create_new_kafka_topic(
            "dummy-compacted", 1, cluster_settings, 1, {"cleanup.policy": "compact"}
        )
        create_new_kafka_topic(
            "dummy-delete", 1, cluster_settings, 1, {"cleanup.policy": "delete"}
        )
        create_new_kafka_topic(
            "dummy-delete-compact",
            1,
            cluster_settings,
            1,
            {"cleanup.policy": "compact,delete"},
        )
        topics = list_topics(cluster_settings)
        assert "dummy-no-settings" in topics


def test_create_update_topic(compose_path):
    with DockerCompose(
        path.abspath(compose_path),
        compose_file_name="docker-compose.yaml",
        wait=True,
        pull=True,
    ) as kafka:
        connection, sr_url = get_connection_details(kafka)
        cluster_settings = {"bootstrap.servers": connection}
        create_new_kafka_topic("dummy-no-settings", 1, cluster_settings, 1, {})
        create_new_kafka_topic(
            "dummy-compacted", 1, cluster_settings, 1, {"cleanup.policy": "compact"}
        )
        create_new_kafka_topic(
            "dummy-delete",
            1,
            cluster_settings,
            1,
            {
                "cleanup.policy": "delete",
                "delete.retention.ms": 7200,
                "compression.type": "lz4",
            },
        )
        create_new_kafka_topic(
            "dummy-delete-compact",
            1,
            cluster_settings,
            1,
            {"cleanup.policy": "compact,delete", "delete.retention.ms": 7200},
        )
        topics = list_topics(cluster_settings)
        assert "dummy-no-settings" in topics
        # Check new partitions and update existing config
        partitions, topic_config = update_kafka_topic(
            "dummy-delete",
            2,
            cluster_settings,
            {"delete.retention.ms": 3600, "compression.type": "lz4"},
        )
        assert partitions == 2
        assert topic_config["delete.retention.ms"].value == "3600"
        assert topic_config["compression.type"].value == "lz4"
        # Check new partitions and adding new setting
        partitions, topic_config = update_kafka_topic(
            "dummy-no-settings",
            4,
            cluster_settings,
            {"compression.type": "gzip"},
        )
        assert partitions == 4
        assert topic_config["compression.type"].value == "gzip"
        # Check delete/reset to default value for property removed
        partitions, topic_config = update_kafka_topic(
            "dummy-delete-compact",
            1,
            cluster_settings,
            {"cleanup.policy": "compact,delete"},
        )
        assert topic_config["delete.retention.ms"].is_default

        partitions, topic_config = update_kafka_topic(
            "dummy-delete",
            2,
            cluster_settings,
            {
                "delete.retention.ms": 3600,
                "compression.type": "lz4",
                "cleanup.policy": "delete,compact",
            },
        )


def test_create_duplicate_topic(compose_path):
    with DockerCompose(
        path.abspath(compose_path),
        compose_file_name="docker-compose.yaml",
        wait=True,
        pull=True,
    ) as kafka:
        connection, sr_url = get_connection_details(kafka)
        cluster_settings = {"bootstrap.servers": connection}
        create_new_kafka_topic("dummy-no-settings", 1, cluster_settings, 1, {})
        list_topics(cluster_settings)
        os.environ["FAIL_IF_ALREADY_EXISTS"] = "True"
        with pytest.raises(KafkaException):
            create_new_kafka_topic("dummy-no-settings", 1, cluster_settings, 1, {})


def test_create_delete_topic(compose_path):
    with DockerCompose(
        path.abspath(compose_path),
        compose_file_name="docker-compose.yaml",
        wait=True,
        pull=True,
    ) as kafka:
        connection, sr_url = get_connection_details(kafka)
        cluster_settings = {"bootstrap.servers": connection}
        create_new_kafka_topic("dummy-to-delete", 1, cluster_settings, 1, {})
        topics = list_topics(cluster_settings)
        assert "dummy-to-delete" in topics
        delete_topic("dummy-to-delete", cluster_settings)
        topics = list_topics(cluster_settings)
        assert "dummy-to-delete" not in topics


def test_delete_non_existing_topic(compose_path):
    with DockerCompose(
        path.abspath(compose_path),
        compose_file_name="docker-compose.yaml",
        wait=True,
        pull=True,
    ) as kafka:
        connection, sr_url = get_connection_details(kafka)
        cluster_settings = {"bootstrap.servers": connection}
        topics = list_topics(cluster_settings)
        assert "dummy-to-delete" not in topics
        delete_topic("dummy-to-delete", cluster_settings)
        topics = list_topics(cluster_settings)
        assert "dummy-to-delete" not in topics
