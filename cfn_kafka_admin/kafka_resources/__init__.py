#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2020-2021 John Mille <john@compose-x.io>

"""Main package to manage Kafka resources"""


from __future__ import annotations

from copy import deepcopy
from typing import Union

try:
    from confluent_kafka.admin import AdminClient, NewTopic
    from confluent_kafka.admin._metadata import ClusterMetadata, TopicMetadata
    from confluent_kafka.cimpl import KafkaError, KafkaException

    USE_CONFLUENT = True
except ImportError as error:
    print("FAILED TO IMPORT CONFLUENT PYTHON", error)
    USE_CONFLUENT = False

from kafka import KafkaConsumer, errors
from kafka.admin import (
    ConfigResource,
    ConfigResourceType,
    KafkaAdminClient,
    NewPartitions,
    NewTopic,
)

KAFKA_TO_CONFLUENT_MAPPING: dict = {
    "bootstrap_servers": "bootstrap.servers",
    "security_protocol": "security.protocol",
    "sasl_mechanism": "sasl.mechanism",
    "sasl_plain_username": "sasl.username",
    "sasl_plain_password": "sasl.password",
}


def convert_kafka_python_to_confluent_kafka(settings: dict) -> dict:
    """Converts the kafka_python cluster info into cluster info for confluent-kafka lib"""
    new_settings: dict = {}
    for _prop, _value in settings.items():
        if _prop not in KAFKA_TO_CONFLUENT_MAPPING:
            new_settings[_prop] = _value
        new_settings[KAFKA_TO_CONFLUENT_MAPPING[_prop]] = _value
    return new_settings


def get_admin_client(settings: dict) -> Union[AdminClient, KafkaAdminClient]:
    """Creates a new Admin client, confluent first if import worked"""
    if USE_CONFLUENT:
        cluster_info = convert_kafka_python_to_confluent_kafka(settings)
        return AdminClient(cluster_info)
    return KafkaAdminClient(**settings)
