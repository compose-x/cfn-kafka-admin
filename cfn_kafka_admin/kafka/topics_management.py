#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2021 John Mille<john@ews-network.net>

"""
Module to handle Kafka topics management.
"""

from kafka import KafkaConsumer, errors
from kafka.admin import (
    ConfigResource,
    ConfigResourceType,
    KafkaAdminClient,
    NewPartitions,
    NewTopic,
)


def create_new_kafka_topic(
    name,
    partitions,
    cluster_info,
    replication_factor=None,
    settings=None,
):
    """
    Function to create new Kafka topic

    :param str name:
    :param int partitions:
    :param dict cluster_info: Dictionary with the Kafka information
    :param int replication_factor: Replication factor. Defaults to 3
    :param dict settings: Additional topics new_settings
    """
    if not replication_factor:
        replication_factor = 1
    try:
        admin_client = KafkaAdminClient(**cluster_info)
        topic = NewTopic(name, partitions, replication_factor, topic_configs=settings)
        admin_client.create_topics([topic])
        return name
    except errors.TopicAlreadyExistsError:
        raise errors.TopicAlreadyExistsError(f"Topic {name} already exists")


def delete_topic(name, cluster_info):
    """
    Function to delete kafka topic

    :param name: name of the topic to delete
    :param cluster_info: cluster information
    :return:
    """
    admin_client = KafkaAdminClient(**cluster_info)
    admin_client.delete_topics([name])


def validate_cleanup_policy(new_value: str, old_value: str, name: str) -> None:
    """
    Validates that the update for cleanup.policy does not go from delete to compact, which is invalid.

    :param str new_value:
    :param str old_value:
    :param str name:
    :raises: ValueError when changing from `delete` to `compact`
    """
    if old_value == "delete" and new_value == "compact":
        raise ValueError(
            name, "You cannot change cleanup.policy from delete to cleanup."
        )


def kafka_update_rules(topic_configs: tuple, new_settings: dict, name: str):
    """
    Ensures update is possible

    :param tuple(str, str, list) topic_configs:
    :param dict new_settings:
    :param str name:
    :return:
    """
    properties = {
        "cleanup.policy": (True, validate_cleanup_policy),
        "compression.type": (False, None),
        "connection.failed.authentication.delay.ms": (False, None),
        "default.replication.factor": (False, None),
        "delete.retention.ms": (True, None),
        "file.delete.delay.ms": (False, None),
        "flush.messages": (False, None),
        "flush.ms": (False, None),
        "group.max.session.timeout.ms": (False, None),
        "index.interval.bytes": (False, None),
        "max.message.bytes": (True, None),
        "max.compaction.lag.ms": (True, None),
        "message.timestamp.type": (True, None),
        "min.cleanable.dirty.ratio": (False, None),
        "min.compaction.lag.ms": (True, None),
        "min.insync.replicas": (True, None),
        "retention.bytes": (True, None),
        "retention.ms": (True, None),
    }
    current_settings = topic_configs[2]
    c_settings_map = {}
    for c_setting in current_settings:
        c_settings_map[c_setting[0]] = c_setting[1]

    for key, new_value in new_settings.items():
        set_value = topic_configs[key]
        if set_value == new_value:
            continue
        else:
            if key not in properties:
                continue
            if not properties[key][0]:
                raise ValueError(name, "Value for", key, "is immutable")
            elif properties[key][0] and properties[key][1]:
                properties[key][1](new_value, set_value, name)


def update_kafka_topic(
    name: str, partitions: int, cluster_info: dict, settings: dict
) -> None:
    """
    Function to update existing Kafka topic

    :param name:
    :param partitions:
    :param cluster_info:
    :param dict settings:
    :return:
    """
    consumer_client = KafkaConsumer(**cluster_info)
    admin_client = KafkaAdminClient(**cluster_info)
    configs = admin_client.describe_configs(
        config_resources=[ConfigResource(ConfigResourceType.TOPIC, name)]
    )
    kafka_update_rules(configs, settings, name)
    curr_partitions = consumer_client.partitions_for_topic(name)
    if curr_partitions:
        curr_partitions_count = len(curr_partitions)
    else:
        raise LookupError(
            f"Failed to retrieve the current number of partitions for {name}"
        )
    if partitions < curr_partitions_count:
        raise ValueError(
            f"The number of partitions set {partitions} for topic "
            f"{name} is lower than current partitions count {curr_partitions} - {curr_partitions_count}"
        )
    elif partitions > curr_partitions_count:
        admin_client = KafkaAdminClient(**cluster_info)
        admin_client.create_partitions({name: NewPartitions(partitions)})
    elif partitions == curr_partitions_count:
        print(
            f"Topic {name} partitions is already set to {curr_partitions} {curr_partitions_count}. Nothing to update"
        )
