# SPDX-License-Identifier: MPL-2.0
# Copyright 2021-2024 John Mille<john@ews-network.net>

from __future__ import annotations

from confluent_kafka.admin import (
    AlterConfigOpType,
    ConfigEntry,
    ConfigResource,
    ResourceType,
)
from confluent_kafka.cimpl import NewPartitions

from cfn_kafka_admin.kafka_resources import get_admin_client
from cfn_kafka_admin.kafka_resources.topics import (
    LOG,
    describe_topic,
    describe_topic_configs,
    wait_for_result,
)


def update_topic_partitions(admin_client, topic_name: str, partitions: int) -> int:
    topic_current_partitions = len(
        describe_topic(admin_client, topic_name, result_only=True).partitions
    )

    if partitions < topic_current_partitions:
        raise ValueError(
            f"The number of partitions set {partitions} for topic "
            f"{topic_name} is lower than current partitions count {topic_current_partitions}"
        )
    elif partitions > topic_current_partitions:
        LOG.info(
            f"{topic_name} - Creating {partitions - topic_current_partitions} new partition(s)"
        )

        wait_for_result(
            admin_client.create_partitions([NewPartitions(topic_name, partitions)])
        )
        final_partitions_count = len(
            describe_topic(admin_client, topic_name, result_only=True).partitions
        )
        LOG.info(f"{topic_name} - new partitions count: {final_partitions_count}")
        return final_partitions_count
    elif partitions == topic_current_partitions:
        LOG.debug(
            f"Topic {topic_name} partitions is already set to {topic_current_partitions}. Nothing to update"
        )
        return topic_current_partitions


def update_kafka_topic(
    topic_name: str,
    partitions: int,
    cluster_info: dict,
    settings: dict,
):
    """
    Function to update existing Kafka topic

    :param topic_name:
    :param partitions:
    :param cluster_info:
    :param dict settings:
    :return:
    """
    topic_config_resource = ConfigResource(ResourceType.TOPIC, topic_name)
    admin_client = get_admin_client(cluster_info, "UPDATE", topic_name)
    topic_configs = describe_topic_configs(admin_client, topic_name, result_only=True)
    incremental_configs: list = []
    for config_name, config_value in topic_configs.items():
        if config_value.is_default and config_name not in settings.keys():
            LOG.debug(
                f"{topic_name} - {config_name} value is default ({config_value.value}) and "
                f"{config_name} not in settings {settings.keys()}"
            )
            continue
        elif not config_value.is_default and config_name not in settings.keys():
            LOG.info(
                f"{topic_name} - {config_name} value is not default ({config_value.value}) and "
                f"{config_name} not in settings {settings.keys()}. Resetting to default value"
            )
            default_entry = ConfigEntry(
                config_name,
                None,
                incremental_operation=AlterConfigOpType["DELETE"],
            )
            incremental_configs.append(default_entry)
            continue
        for setting_name, setting_value in settings.items():
            if not setting_name == config_name:
                continue
            if str(setting_value) != config_value.value:
                LOG.info(
                    f"Value for {setting_name} is different(current->new): {config_value}->{setting_value}"
                )
                new_config = ConfigEntry(
                    config_name,
                    str(setting_value),
                    incremental_operation=AlterConfigOpType["SET"],
                )
                incremental_configs.append(new_config)
    for _incremental_config in incremental_configs:
        try:
            wait_for_result(
                admin_client.incremental_alter_configs(
                    [
                        ConfigResource(
                            ResourceType.TOPIC,
                            topic_name,
                            incremental_configs=[_incremental_config],
                        )
                    ]
                )
            )
        except Exception as error:
            LOG.error(
                f"Error updating topic {topic_name} property {_incremental_config.name}={_incremental_config.value}: {error}"
            )
            LOG.exception(error)
    partitions = update_topic_partitions(admin_client, topic_name, partitions)
    new_topic_configs = describe_topic_configs(
        admin_client, topic_name, result_only=True
    )
    LOG.debug(new_topic_configs)
    return partitions, new_topic_configs
