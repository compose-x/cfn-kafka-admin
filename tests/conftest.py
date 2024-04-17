"""Pytest configuration and hooks"""

from os import path

import pytest

HERE = path.abspath(path.dirname(__file__))


@pytest.fixture(scope="session")
def compose_path() -> str:
    return path.abspath(path.join(HERE, "../"))


@pytest.fixture(scope="session")
def schema_sample():
    return {
        "type": "record",
        "namespace": "com.mycorp.mynamespace",
        "name": "value_test_subject",
        "doc": "Sample schema to help you get started.",
        "fields": [
            {
                "name": "myField1",
                "type": "int",
                "doc": "The int type is a 32-bit signed integer.",
            },
            {
                "name": "myField2",
                "type": "double",
                "doc": "The double type is a double precision (64-bit) IEEE 754 floating-point number.",
            },
            {
                "name": "myField3",
                "type": "string",
                "doc": "The string is a unicode character sequence.",
            },
        ],
    }
