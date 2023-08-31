"""Tests topics creation, delete and update"""

import pytest
from confluent_kafka.admin import AdminClient as ConfluentAdminClient
from kafka import errors
from testcontainers.kafka import KafkaContainer

from cfn_kafka_admin.kafka_resources import (
    convert_kafka_python_to_confluent_kafka,
    get_admin_client,
)
from cfn_kafka_admin.kafka_resources.topics_management import (
    create_new_kafka_topic,
    delete_topic,
)


def list_topics(con_settings: dict):
    client = get_admin_client(con_settings)
    if isinstance(client, ConfluentAdminClient):
        res = client.list_topics()
        for _topic in res.topics.values():
            print(_topic.topic, len(_topic.partitions))
        return res.topics


def test_create_topic():
    with KafkaContainer("confluentinc/cp-kafka:7.4.0") as kafka:
        connection = kafka.get_bootstrap_server()
        cluster_settings = {"bootstrap_servers": connection}
        create_new_kafka_topic("dummy-no-settings", 1, cluster_settings, 1, {})
        topics = list_topics(cluster_settings)
        assert "dummy-no-settings" in topics


def test_create_duplicate_topic():
    with KafkaContainer("confluentinc/cp-kafka:7.4.0") as kafka:
        connection = kafka.get_bootstrap_server()
        cluster_settings = {"bootstrap_servers": connection}
        create_new_kafka_topic("dummy-no-settings", 1, cluster_settings, 1, {})
        list_topics(cluster_settings)
        with pytest.raises(errors.TopicAlreadyExistsError):
            create_new_kafka_topic("dummy-no-settings", 1, cluster_settings, 1, {})


def test_create_delete_topic():
    with KafkaContainer("confluentinc/cp-kafka:7.4.0") as kafka:
        connection = kafka.get_bootstrap_server()
        cluster_settings = {"bootstrap_servers": connection}
        create_new_kafka_topic("dummy-to-delete", 1, cluster_settings, 1, {})
        topics = list_topics(cluster_settings)
        assert "dummy-to-delete" in topics
        delete_topic("dummy-to-delete", cluster_settings)
        topics = list_topics(cluster_settings)
        assert "dummy-to-delete" not in topics


def test_delete_non_existing_topic():
    with KafkaContainer("confluentinc/cp-kafka:7.4.0") as kafka:
        connection = kafka.get_bootstrap_server()
        cluster_settings = {"bootstrap_servers": connection}
        topics = list_topics(cluster_settings)
        assert "dummy-to-delete" not in topics
        delete_topic("dummy-to-delete", cluster_settings)
        topics = list_topics(cluster_settings)
        assert "dummy-to-delete" not in topics