#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2020-2021 John Mille <john@ews-network.net>

"""Top-level package for Kafka::Topic."""

from troposphere import AWSProperty

__author__ = """John Mille"""
__email__ = "john@ews-network.net"
__version__ = "0.2.0"


class KafkaAclPolicy(AWSProperty):
    """
    Class to represent a policy for EWS::Kafka::ACL.Policies
    """

    props = {
        "Resource": (str, True),
        "PatternType": (str, False),
        "Principal": (str, True),
        "ResourceType": (str, True),
        "Action": (str, True),
        "Effect": (str, True),
        "Host": (str, False),
    }
