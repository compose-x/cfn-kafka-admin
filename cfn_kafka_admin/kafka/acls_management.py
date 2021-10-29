#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2021 John Mille<john@ews-network.net>

"""
Module to handle Kafka topics management.
"""

from kafka.admin import (
    ACL,
    ACLFilter,
    ACLOperation,
    ACLPermissionType,
    ACLResourcePatternType,
    KafkaAdminClient,
    ResourcePattern,
    ResourcePatternFilter,
    ResourceType,
)


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


def create_new_acls(acls, cluster_info):
    """
    Function to iterate over the given ACL policies and apply them

    :param list acls:
    :param cluster_info:
    :return:
    """
    admin_client = KafkaAdminClient(**cluster_info)
    kafka_acls = []
    for policy in acls:
        if isinstance(policy, dict):
            new_acl = ACL(
                principal=policy["Principal"],
                host=policy["Host"],
                operation=ACLOperation[policy["Action"]],
                permission_type=ACLPermissionType[policy["Effect"]],
                resource_pattern=ResourcePattern(
                    resource_type=ResourceType[policy["ResourceType"]],
                    resource_name=policy["Resource"],
                    pattern_type=ACLResourcePatternType[policy["PatternType"]],
                ),
            )
            kafka_acls.append(new_acl)
    admin_client.create_acls(kafka_acls)


def delete_acls(acls, cluster_info):
    """
    Function to delete the ACLs.
    :param acls:
    :param cluster_info:
    :return:
    """
    admin_client = KafkaAdminClient(**cluster_info)
    policies = []
    for policy in acls:
        new_filter = ACLFilter(
            principal=policy["Principal"],
            host=policy["Host"] if "Host" in policy else "*",
            operation=ACLOperation[policy["Action"]],
            permission_type=ACLPermissionType[policy["Effect"]],
            resource_pattern=ResourcePatternFilter(
                resource_type=ResourceType[policy["ResourceType"]],
                resource_name=policy["Resource"],
                pattern_type=ACLResourcePatternType[policy["PatternType"]],
            ),
        )
        policies.append(new_filter)
    admin_client.delete_acls(policies)
