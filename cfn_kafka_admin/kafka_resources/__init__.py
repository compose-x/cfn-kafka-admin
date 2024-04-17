#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2020-2021 John Mille <john@compose-x.io>

"""Main package to manage Kafka resources"""

from __future__ import annotations

import os
from copy import deepcopy

from confluent_kafka.admin import AdminClient


def get_admin_client(
    settings: dict, resource: str, operation: str, resource_dest: str = None
) -> AdminClient:
    """Creates a new Admin client, confluent first if import worked"""
    client_id: str = f"LAMBDA_{resource}_{operation}"
    if resource_dest:
        client_id += f"_{resource_dest}"
    timeout_ms_env = int(os.environ.get("ADMIN_REQUEST_TIMEOUT_MS", 60000))
    cluster_info = deepcopy(settings)

    if "client.id" not in settings:
        settings.update({"client.id": client_id})
    # cluster_info.update({"debug": "broker,admin"})
    else:
        cluster_info = settings
    cluster_info.update(
        {"request.timeout.ms": timeout_ms_env if timeout_ms_env >= 60000 else 60000}
    )
    return AdminClient(cluster_info)
