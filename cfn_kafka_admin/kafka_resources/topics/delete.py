# SPDX-License-Identifier: MPL-2.0
# Copyright 2021-2024 John Mille<john@ews-network.net>

from __future__ import annotations

from time import sleep

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import ConfigResource, ResourceType
from retry import retry

from cfn_kafka_admin.kafka_resources import get_admin_client
from cfn_kafka_admin.kafka_resources.topics import (
    LOG,
    RETRY_ATTEMPTS,
    RETRY_JITTER,
    describe_topic_configs,
    wait_for_result,
)


@retry(
    (KafkaException,),
    tries=RETRY_ATTEMPTS,
    jitter=RETRY_JITTER,
    logger=LOG,
)
def delete_topic(topic_name: str, cluster_info: dict):
    """Function to delete kafka topic"""
    admin_client = get_admin_client(cluster_info, "DELETE", topic_name)
    try:
        configs = describe_topic_configs(admin_client, topic_name, result_only=True)
        LOG.info(f"Deleting topic: {topic_name}")
        LOG.debug(f"{topic_name} => {configs}")
    except KafkaException as error:
        if error.args[0] == KafkaError.UNKNOWN_TOPIC_OR_PART:
            LOG.info(f"Topic did not exist: {topic_name}")
            return
        raise
    try:
        wait_for_result(admin_client.delete_topics([topic_name]))
        sleep(1)
        LOG.info("Trying to check topic is gone with describe")
    except Exception as error:
        LOG.error(f"Failed to delete topic {topic_name}")
        LOG.exception(error)
        raise
    try:
        wait_for_result(
            admin_client.describe_configs(
                [ConfigResource(ResourceType.TOPIC, topic_name)]
            )
        )
    except KafkaException as error:
        if error.args[0] == KafkaError.UNKNOWN_TOPIC_OR_PART:
            LOG.info(f"Topic successfully deleted: {topic_name}")
            return
        LOG.error(f"Topic describe {topic_name} failed")
        LOG.exception(error)
        raise
