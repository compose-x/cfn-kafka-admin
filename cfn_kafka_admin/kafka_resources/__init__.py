#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2020-2021 John Mille <john@compose-x.io>

"""Main package to manage Kafka resources"""

from __future__ import annotations

import os

from confluent_kafka.admin import AdminClient

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
        else:
            new_settings[KAFKA_TO_CONFLUENT_MAPPING[_prop]] = _value
    return new_settings


def get_admin_client(
    settings: dict, operation: str, topic_dest: str, convert_props: bool = True
) -> AdminClient:
    """Creates a new Admin client, confluent first if import worked"""
    client_id: str = f"LAMBDA_{operation}_{topic_dest}"
    timeout_ms_env = int(os.environ.get("ADMIN_REQUEST_TIMEOUT_MS", 60000))
    if convert_props:
        cluster_info = convert_kafka_python_to_confluent_kafka(settings)
        if "client.id" not in settings:
            settings.update({"client.id": client_id})
    # cluster_info.update({"debug": "broker,admin"})
    else:
        cluster_info = settings
    cluster_info.update(
        {"request.timeout.ms": timeout_ms_env if timeout_ms_env >= 60000 else 60000}
    )
    return AdminClient(cluster_info)
