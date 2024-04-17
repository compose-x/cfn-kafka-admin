# Copyright 2021-2024 John Mille<john@ews-network.net>

"""
Module to handle Kafka topics management.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from confluent_kafka.admin import AdminClient
    from concurrent.futures import Future

from confluent_kafka.admin import (
    AclBinding,
    AclBindingFilter,
    AclOperation,
    AclPermissionType,
)

from cfn_kafka_admin.kafka_resources import get_admin_client


def get_acls_admin_client(
    acls: list[dict], operation: str, cluster_info: dict
) -> AdminClient:
    if acls:
        resource_name: str = (
            f'{acls[0]["Principal"]}_{acls[0]["Resource"]}_{acls[0]["Action"]}'
        )
    else:
        resource_name = "unspecified"
    admin_client: AdminClient = get_admin_client(
        cluster_info, "ACLs", operation, resource_name
    )
    return admin_client


def differentiate_old_new_acls(new_policies, old_policies):
    """
    Function to differentiate with ACLs are common and shall be kept, which ones are to be added and then removed.

    :param list new_policies:
    :param list old_policies:
    :return: the new acls and old acls
    :rtype: tuple
    """

    common_policies = [d for d in new_policies if d in old_policies]
    common_policies_set = set()
    for policy in common_policies:
        common_policies_set.add(tuple(policy.items()))
    new_policies_set = set()
    old_policies_set = set()
    for policy in new_policies:
        t_policy = tuple(policy.items())
        if t_policy not in new_policies_set or t_policy in common_policies:
            new_policies_set.add(t_policy)
    for policy in old_policies:
        t_policy = tuple(policy.items())
        if (
            t_policy not in old_policies_set
            and t_policy not in common_policies
            and t_policy not in new_policies_set
        ):
            old_policies_set.add(t_policy)
    final_delete_acls = [dict(k) for k in old_policies_set]
    final_new_acls = [dict(k) for k in new_policies_set]
    return final_new_acls, final_delete_acls


def set_binding_from_dict(policy: dict) -> AclBinding:
    new_acl: AclBinding = AclBinding(
        restype=policy["ResourceType"],
        name=policy["Resource"],
        principal=policy["Principal"],
        host=policy["Host"] if "Host" in policy else "*",
        operation=AclOperation[policy["Action"]],
        permission_type=AclPermissionType[policy["Effect"]],
        resource_pattern_type=policy["PatternType"],
    )
    return new_acl


def set_binding_filter_from_dict(policy: dict) -> AclBindingFilter:
    acl_filter: AclBindingFilter = AclBindingFilter(
        restype=policy["ResourceType"],
        name=policy["Resource"],
        principal=policy["Principal"],
        host=policy["Host"] if "Host" in policy else "*",
        operation=AclOperation[policy["Action"]],
        permission_type=AclPermissionType[policy["Effect"]],
        resource_pattern_type=policy["PatternType"],
    )
    return acl_filter


def create_new_acls(acls, cluster_info):
    """
    Function to iterate over the given ACL policies and apply them

    :param list acls:
    :param cluster_info:
    :return:
    """
    admin_client: AdminClient = get_acls_admin_client(acls, "CREATE", cluster_info)
    kafka_acls = []
    for policy in acls:
        if isinstance(policy, dict):
            new_acl: AclBinding = set_binding_from_dict(policy)
            kafka_acls.append(new_acl)
    return_vals = admin_client.create_acls(kafka_acls)
    for acl_binding, _future in return_vals.items():
        if _future.exception():
            raise _future.exception()


def delete_acls(acls: list[dict], cluster_info: dict) -> dict[AclBindingFilter, Future]:
    """Function to delete the ACLs."""
    admin_client: AdminClient = get_acls_admin_client(acls, "DELETE", cluster_info)
    policies = []
    for policy in acls:
        new_filter = set_binding_filter_from_dict(policy)
        policies.append(new_filter)
    deleted: dict[AclBindingFilter, Future] = admin_client.delete_acls(policies)
    for _filter, _future in deleted.items():
        while not _future.done():
            pass
    return deleted
