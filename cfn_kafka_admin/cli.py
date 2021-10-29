#  -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
# Copyright 2020-2021 John Mille <john@ews-network.net>

"""Console script for aws_cfn_kafka_admin_provider."""

import argparse
import pprint
import sys

from cfn_kafka_admin.cfn_kafka_admin import KafkaStack


def main():
    """Console script for aws_cfn_kafka_admin_provider."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--definition-file",
        dest="files_paths",
        required=True,
        help="Path to the Topics / ACLs definition files",
        action="append",
    )
    parser.add_argument(
        "--config",
        "--config-file-path",
        required=False,
        dest="config_path",
        help="Override file path to the kafka definition file",
        default=None,
    )
    parser.add_argument(
        "-o", "--output-file", dest="output_file", help="Path to file output"
    )
    parser.add_argument(
        "--format",
        dest="format",
        help="Template format",
        default="json",
        choices=["json", "yaml"],
    )
    parser.add_argument("_", nargs="*")
    args = parser.parse_args()

    stack = KafkaStack(args.files_paths, args.config_path)
    stack.render_topics()
    stack.render_acls()
    if args.output_file:
        with open(args.output_file, "w") as output_fd:
            if args.format == "yaml":
                output_fd.write(stack.template.to_yaml())
            else:
                output_fd.write(stack.template.to_json())
    else:
        if args.format == "yaml":
            print(stack.template.to_yaml())
        else:
            try:
                print(stack.template.to_json())
            except TypeError:
                pprint.pprint(stack.template.to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
