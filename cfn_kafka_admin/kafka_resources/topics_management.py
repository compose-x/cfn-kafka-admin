# SPDX-License-Identifier: MPL-2.0
# Copyright 2021 John Mille<john@ews-network.net>

"""
Module to handle Kafka topics management.
"""

from __future__ import annotations

import datetime
import logging
import os
from os import environ
from random import randint
from time import sleep
from typing import TYPE_CHECKING, Union

try:
    from confluent_kafka.admin import AdminClient
    from confluent_kafka.admin import ConfigResource as ConfluentConfigResource
    from confluent_kafka.admin import NewTopic as ConfluentNewTopic
    from confluent_kafka.admin._metadata import ClusterMetadata, TopicMetadata
    from confluent_kafka.admin._resource import ResourceType
    from confluent_kafka.cimpl import KafkaError as ConfluentKafkaError
    from confluent_kafka.cimpl import KafkaException as ConfluentKafkaException

    USE_CONFLUENT = False
except ImportError as import_error:
    print("FAILED TO IMPORT CONFLUENT PYTHON", import_error)
    USE_CONFLUENT = False

from kafka import KafkaConsumer, errors
from kafka.admin import (
    ConfigResource,
    ConfigResourceType,
    KafkaAdminClient,
    NewPartitions,
    NewTopic,
)
from retry import retry

from cfn_kafka_admin.common import KAFKA_LOG, setup_logging
from cfn_kafka_admin.kafka_resources import get_admin_client

LOG = setup_logging(__file__)

KAFKA_LOG.setLevel(logging.WARNING)
KAFKA_DEBUG = environ.get("DEBUG_KAFKA_CLIENT", False)
if KAFKA_DEBUG:
    KAFKA_LOG.setLevel(logging.DEBUG)
    KAFKA_LOG.handlers[0].setLevel(logging.DEBUG)

RETRY_ATTEMPTS = max(abs(int(environ.get("CREATE_RETRY_ATTEMPTS", 3))), 5)
RETRY_JITTER = randint(1, 5)


@retry(
    (
        errors.KafkaError,
        ConfluentKafkaException,
    ),
    # tries=RETRY_ATTEMPTS,
    jitter=RETRY_JITTER,
    logger=LOG,
)
def create_new_kafka_topic(
    name,
    partitions: int,
    cluster_info: dict,
    replication_factor: int = 1,
    topic_config: dict = None,
) -> str:
    """
    Function to create new Kafka topic

    :param str name:
    :param int partitions:
    :param dict cluster_info: Dictionary with the Kafka information
    :param int replication_factor: Replication factor. Defaults to 3
    :param dict topic_config: Additional topics new_settings
    """
    if replication_factor < 0:
        raise ValueError("Topic partitions must be >= 1")
    LOG.info(
        "Attempting to create topic:(partitions/replication/settings): {}: {}/{}/{}".format(
            name, partitions, replication_factor, topic_config
        )
    )

    admin_client = get_admin_client(cluster_info, "CREATE", name)
    if isinstance(admin_client, KafkaAdminClient):
        LOG.info("Create: Using kafka-python lib.")
        try:
            topic = NewTopic(
                name, partitions, replication_factor, topic_configs=topic_config
            )
            admin_client.create_topics([topic])
            LOG.info(
                "Successfully created topic:(partitions/replication): {}: {}/{}".format(
                    name, partitions, replication_factor
                )
            )
            return name
        except errors.TopicAlreadyExistsError as error:
            LOG.exception(error)
            LOG.error(
                LOG.info(
                    "Failed to create topic:(partitions/replication): {}: {}/{}".format(
                        name, partitions, replication_factor
                    )
                )
            )
            raise errors.TopicAlreadyExistsError(f"Topic {name} already exists")
    else:
        LOG.info("Using confluent-kafka python lib.")
        if topic_config:
            new_topic = ConfluentNewTopic(
                name, partitions, replication_factor, config=topic_config
            )
        else:
            new_topic = ConfluentNewTopic(name, partitions, replication_factor)
        ret = admin_client.create_topics([new_topic], validate_only=False)
        for _topic, fnc in ret.items():
            try:
                while not fnc.done():
                    fnc.result()
            except ConfluentKafkaException as create_error:
                LOG.exception(create_error)
                if create_error.args[0] == ConfluentKafkaError.TOPIC_ALREADY_EXISTS:
                    if environ.get("FAIL_IF_ALREADY_EXISTS", None) is None:
                        return name
                    else:
                        raise errors.TopicAlreadyExistsError(
                            f"Topic {name} already exists"
                        )
                raise errors.KafkaConnectionError(f"Failed to create topic {name}")
        _wait_time = abs(
            int(os.environ.get("CREATE_DESCRIBE_WAIT_TIME", RETRY_JITTER + 2))
        )
        LOG.info(f"CREATE {name} - Waiting {_wait_time} before validation")
        sleep(0)
        validate_topic_created(admin_client, name)
        return name


@retry(
    (
        errors.KafkaError,
        ConfluentKafkaException,
    ),
    # tries=RETRY_ATTEMPTS,
    jitter=RETRY_JITTER,
    logger=LOG,
)
def validate_topic_created(admin_client, topic: str):
    try:
        desc = admin_client.describe_configs(
            [ConfluentConfigResource(ResourceType.TOPIC, topic)]
        )
        for _config in desc.values():
            while not _config.done():
                _config.result()
            LOG.info(f"Confluent LIB. Created topic: {topic} - {_config.result()}")
    except ConfluentKafkaException as describe_error:
        LOG.error(f"Create {topic}: Failed at describe validation.")
        LOG.exception(describe_error)
        if describe_error.args[0] == ConfluentKafkaError.UNKNOWN_TOPIC_OR_PART:
            LOG.error(f"Failed to describe topic {topic}")
        raise describe_error


@retry(
    (
        errors.KafkaError,
        ConfluentKafkaException,
    ),
    tries=RETRY_ATTEMPTS,
    jitter=RETRY_JITTER,
    logger=LOG,
)
def delete_topic(name, cluster_info):
    """
    Function to delete kafka topic

    :param name: name of the topic to delete
    :param cluster_info: cluster information
    """
    admin_client = get_admin_client(cluster_info, "DELETE", name)
    if isinstance(admin_client, KafkaAdminClient):
        LOG.info("Delete: using kafka-python lib.")
        LOG.info(f"Deleting Topic {name}")
        try:
            admin_client.delete_topics([name])
            LOG.debug(f"Successfully deleted topic: {name}")
        except errors.UnknownTopicOrPartitionError:
            LOG.error(f"Topic {name} does not exist. Nothing to delete")
        except Exception as error:
            LOG.exception(error)
            raise
    else:
        LOG.info("Delete: using confluent-kafka python lib.")
        try:
            desc = admin_client.describe_configs(
                [ConfluentConfigResource(ResourceType.TOPIC, name)]
            )
            for _config in desc.values():
                while not _config.done():
                    _config.result()
                LOG.info(f"Confluent LIB. Deleting topic: {name} - {_config.result()}")
        except ConfluentKafkaException as error:
            if error.args[0] == ConfluentKafkaError.UNKNOWN_TOPIC_OR_PART:
                LOG.info(f"Topic did not exist: {name}")
                return
            raise
        try:
            ret = admin_client.delete_topics([name])
            for _topic, fnc in ret.items():
                while not fnc.done():
                    fnc.result()
            sleep(1)
            LOG.info("Trying to check topic is gone with describe")
        except Exception as error:
            LOG.error(f"Failed to delete topic {name}")
            LOG.exception(error)
            raise
        try:
            desc = admin_client.describe_configs(
                [ConfluentConfigResource(ResourceType.TOPIC, name)]
            )
            for _config in desc.values():
                while not _config.done():
                    _config.result()
        except ConfluentKafkaException as error:
            if error.args[0] == ConfluentKafkaError.UNKNOWN_TOPIC_OR_PART:
                LOG.info(f"Topic successfully deleted: {name}")
                return
            LOG.error(f"Topic describe {name} failed")
            LOG.exception(error)
            raise


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
