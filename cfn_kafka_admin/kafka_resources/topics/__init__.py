# SPDX-License-Identifier: MPL-2.0
# Copyright 2021-2024 John Mille<john@ews-network.net>

"""
Module to handle Kafka topics management.
"""

from __future__ import annotations

import logging
from os import environ
from random import randint

from confluent_kafka import TopicCollection
from confluent_kafka.admin import ConfigResource, ResourceType

from cfn_kafka_admin.common import KAFKA_LOG, setup_logging

LOG = setup_logging(__file__)

KAFKA_LOG.setLevel(logging.WARNING)
KAFKA_DEBUG = environ.get("DEBUG_KAFKA_CLIENT", False)
if KAFKA_DEBUG:
    KAFKA_LOG.setLevel(logging.DEBUG)
    KAFKA_LOG.handlers[0].setLevel(logging.DEBUG)

RETRY_ATTEMPTS = max(abs(int(environ.get("CREATE_RETRY_ATTEMPTS", 3))), 5)
RETRY_JITTER = randint(1, 5)


def wait_for_result(result_container: dict) -> dict:
    for _future in result_container.values():
        while not _future.done():
            _future.result()
    return result_container


def describe_topic_configs(admin_client, topic_name, result_only: bool = False) -> dict:
    """
    Function to describe a topic
    """
    topic_config_resource = ConfigResource(ResourceType.TOPIC, topic_name)
    config = wait_for_result(admin_client.describe_configs([topic_config_resource]))
    if result_only:
        return config[topic_config_resource].result()
    return config


def describe_topic(admin_client, topic_name: str, result_only: bool = False):
    """
    Function to describe a topic
    """
    desc_topic = wait_for_result(
        admin_client.describe_topics(TopicCollection([topic_name]))
    )
    if result_only:
        return desc_topic[topic_name].result()
    return desc_topic
