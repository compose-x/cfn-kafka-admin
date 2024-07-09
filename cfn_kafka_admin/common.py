#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2020-2024 John Mille <john@compose-x.io>

from __future__ import annotations

import logging as logthings
import re
import sys
from copy import deepcopy


class MyFormatter(logthings.Formatter):
    default_format = "%(asctime)s [%(levelname)8s] %(message)s"
    debug_format = "%(asctime)s [%(levelname)8s] (%(filename)s.%(lineno)d , %(funcName)s,) %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def _filter_out(cls, record: str):
        if not isinstance(record, str):
            return record
        jwt = re.compile(r"eyJ(.*)[\w]+")
        password_dict_value = re.compile(r"(.*)password\':(.*)\'(?P<password>.*)\'")
        __filters = [jwt, password_dict_value]
        for _filter in __filters:
            if _filter.match(record):
                return _filter.sub("******", record)
        return record

    def _filter(self, record):
        record.msg = self._filter_out(record.msg)
        if isinstance(record.args, dict):
            args = deepcopy(record.args)
            for k, v in record.args.items():
                if k.find("password") >= 0:
                    args[k] = "******"
                else:
                    args[k] = self._filter_out(v)
            record.args = args
        else:
            record.args = tuple(self._filter_out(arg) for arg in record.args)

    def format(self, record) -> str:
        self._filter(record)
        if record.levelno == logthings.DEBUG:
            formatter = logthings.Formatter(self.debug_format, self.date_format)
        else:
            formatter = logthings.Formatter(self.default_format, self.date_format)
        return formatter.format(record)


class InfoFilter(logthings.Filter):
    """Inspired from https://stackoverflow.com/a/16066513"""

    def filter(self, rec):
        return rec.levelno in (logthings.DEBUG, logthings.INFO)


class ErrorFilter(logthings.Filter):
    """Inspired from https://stackoverflow.com/a/16066513"""

    def filter(self, rec):
        return rec.levelno not in (logthings.DEBUG, logthings.INFO)


def setup_logging(logger_name: str = "kafka"):
    root_logger = logthings.getLogger()
    for h in root_logger.handlers:
        root_logger.removeHandler(h)

    app_logger = logthings.getLogger(logger_name)

    for h in app_logger.handlers:
        app_logger.removeHandler(h)

    stdout_handler = logthings.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(MyFormatter())
    stdout_handler.setLevel(logthings.INFO)
    stdout_handler.addFilter(InfoFilter())

    stderr_handler = logthings.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(MyFormatter())
    stderr_handler.setLevel(logthings.WARNING)
    stderr_handler.addFilter(ErrorFilter())

    app_logger.addHandler(stdout_handler)
    app_logger.addHandler(stderr_handler)
    app_logger.setLevel(logthings.DEBUG)
    return app_logger


KAFKA_LOG = setup_logging()


def recursive_merge(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            dict1[key] = recursive_merge(dict1[key], value)
        else:
            # Merge non-dictionary values
            dict1[key] = value
    return dict1
