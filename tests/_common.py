from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from testcontainers.compose import DockerCompose


def get_connection_details(docker_compose: DockerCompose):
    sr_port = int(docker_compose.get_service_port("schema-registry", 8081))
    kafka_port = int(docker_compose.get_service_port("broker", 9092))
    base_url: str = f"http://localhost:{sr_port}"
    docker_compose.wait_for(f"{base_url}/subjects")

    bootstrap_endpoint = f"localhost:{kafka_port}"
    return bootstrap_endpoint, base_url
