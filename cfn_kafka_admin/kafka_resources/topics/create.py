# SPDX-License-Identifier: MPL-2.0
# Copyright 2021-2024 John Mille<john@ews-network.net>

from __future__ import annotations

from os import environ

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import ConfigResource, ResourceType
from confluent_kafka.cimpl import NewTopic
from retry import retry

from cfn_kafka_admin.kafka_resources import get_admin_client
from cfn_kafka_admin.kafka_resources.topics import (
    LOG,
    RETRY_ATTEMPTS,
    RETRY_JITTER,
    wait_for_result,
)


@retry(
    (KafkaException,),
    tries=RETRY_ATTEMPTS,
    jitter=RETRY_JITTER,
    logger=LOG,
)
def create_new_kafka_topic(
    topic_name,
    partitions: int,
    cluster_info: dict,
    replication_factor: int = 1,
    topic_config: dict = None,
) -> str:
    """
    Function to create new Kafka topic

    :param str topic_name:
    :param int partitions:
    :param dict cluster_info: Dictionary with the Kafka information
    :param int replication_factor: Replication factor. Defaults to 3
    :param dict topic_config: Additional topics new_settings
    """
    if replication_factor < 0:
        raise ValueError("Topic partitions must be >= 1")
    LOG.info(
        "Attempting to create topic:(partitions/replication/settings): {}: {}/{}/{}".format(
            topic_name, partitions, replication_factor, topic_config
        )
    )
    admin_client = get_admin_client(cluster_info, "CREATE", topic_name)

    if topic_config:
        new_topic = NewTopic(
            topic_name, partitions, replication_factor, config=topic_config
        )
    else:
        new_topic = NewTopic(topic_name, partitions, replication_factor)
    try:
        wait_for_result(admin_client.create_topics([new_topic], validate_only=False))
    except KafkaException as create_error:
        LOG.exception(create_error)
        if create_error.args[0] == KafkaError.TOPIC_ALREADY_EXISTS:
            if environ.get("FAIL_IF_ALREADY_EXISTS", None) is None:
                return topic_name
            else:
                raise create_error
        raise create_error
    topic_config_resource = ConfigResource(ResourceType.TOPIC, topic_name)
    created_topic_config = validate_topic_created(admin_client, topic_config_resource)
    LOG.debug(created_topic_config)
    return topic_name


@retry(
    (KafkaError,),
    tries=RETRY_ATTEMPTS,
    jitter=RETRY_JITTER,
    logger=LOG,
)
def validate_topic_created(admin_client, topic_config_resource: ConfigResource):
    try:
        desc = wait_for_result(admin_client.describe_configs([topic_config_resource]))
        LOG.info("Created topic: " f"{topic_config_resource.name}")
        return desc[topic_config_resource].result()
    except KafkaException as describe_error:
        LOG.error(
            f"Create {topic_config_resource.name}: Failed at describe validation."
        )
        LOG.exception(describe_error)
        if describe_error.args[0] == KafkaError.UNKNOWN_TOPIC_OR_PART:
            LOG.error(f"Failed to describe topic {topic_config_resource.name}")
        raise describe_error
