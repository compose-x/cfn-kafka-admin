#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2021 John Mille<john@ews-network.net>

"""
Module to handle Kafka topics management.
"""

from kafka import KafkaConsumer, errors
from kafka.admin import KafkaAdminClient, NewPartitions, NewTopic


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
    :param dict settings: Additional topics settings
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
    print(f"Deleting topic {name}")
    admin_client = KafkaAdminClient(**cluster_info)
    admin_client.delete_topics([name])


def update_kafka_topic(name, partitions, cluster_info):
    """
    Function to update existing Kafka topic

    :param name:
    :param partitions:
    :param cluster_info:
    :return:
    """
    consumer_client = KafkaConsumer(**cluster_info)
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
