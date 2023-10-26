#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2020-2021 John Mille <john@compose-x.io>

"""Main package to manage Kafka resources"""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Union

try:
    from confluent_kafka.admin import AdminClient

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
    "client_id": "client.id",
}


def convert_kafka_python_to_confluent_kafka(settings: dict) -> dict:
    """Converts the kafka_python cluster info into cluster info for confluent-kafka lib"""
    new_settings: dict = {}
    for _prop, _value in settings.items():
        if _prop not in KAFKA_TO_CONFLUENT_MAPPING:
            new_settings[_prop] = _value
        new_settings[KAFKA_TO_CONFLUENT_MAPPING[_prop]] = _value
    return new_settings


def get_admin_client(
    settings: dict, operation: str, topic_dest: str
) -> Union[AdminClient, KafkaAdminClient]:
    """Creates a new Admin client, confluent first if import worked"""
    client_id: str = f"LAMBDA_{operation}_{topic_dest}"
    timeout_ms_env = int(os.environ.get("ADMIN_REQUEST_TIMEOUT_MS", 60000))
    print(f"REQUEST TIMEOUT MS: {timeout_ms_env}")
    settings.update({"client_id": client_id})
    if USE_CONFLUENT:
        cluster_info = convert_kafka_python_to_confluent_kafka(settings)
        # cluster_info.update({"debug": "broker,admin"})
        cluster_info.update(
            {"request.timeout.ms": timeout_ms_env if timeout_ms_env >= 60000 else 60000}
        )
        return AdminClient(cluster_info)
    return KafkaAdminClient(**settings)
