
.. meta::
    :description: CFN Kafka Admin
    :keywords: AWS, CloudFormation, Kafka, Topics, ACL, Schema

=====================================================
Welcome to cfn-kafka-admin's documentation!
=====================================================

|PYPI_VERSION| |FOSSA| |PYPI_LICENSE|

|CODE_STYLE| |TDD|

.. image:: https://codebuild.eu-west-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiY2xwc0NER1JuU1J3MThYczhFMDJLWlQxWGpoRnhNWHNtbGN1NGpVMVNTMk12UlQxdWVlZ2w5YnhPQzhkMnV4cTI0S0tIdTRyTmRHWWErWXJPNWFpcWlzPSIsIml2UGFyYW1ldGVyU3BlYyI6IkxaRGZCMW1KbVE1RWRJYjciLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main
        :target: https://eu-west-1.codebuild.aws.amazon.com/project/eyJlbmNyeXB0ZWREYXRhIjoibVAvWVBBNjZlNWFwTWEwSEdWcGx6MWpudy9KeEZTb1lXdWFuQ3FwbjJCRTBnc1lyZm41eHRqV2k0bDN6UTBmaEpJMGd0Y3I3Vm5kTGtZQzc1b25Uckxxd3hERzlpSzJndVFOekJUR0NMM0V0YXljSWx4Yjc2YmJpUzlZM01RPT0iLCJpdlBhcmFtZXRlclNwZWMiOiI3bnllb1dlbU8rZis1ekh5IiwibWF0ZXJpYWxTZXRTZXJpYWwiOjF9

----------------------------------------------------------------------
Manage Apache Kafka topics, schemas and ACLs from AWS CloudFormation
----------------------------------------------------------------------

This project was built to

* Control ACLs, Topics and Schemas via GitOps and controlled "as code" in AWS CloudFormation
* Allow non-kafka power users to have a simple declarative way to define what they need in Kafka

Install
=========

To install the CLI, simply run

.. code-block:: bash

    pip install cfn-kafka-admin


To install the lambda functions, see :ref:`functions_installation`

Usage
======

This project is made of two parts that will allow you to manage ACLs, Topics and their associated schemas, using
AWS CloudFormation.

If you are using AWS MSK, which we highly recommend, a majority of these functionalities can be done with native AWS
implementations. However, this has been used and tested with MSK too and works (schemas excluded, see `AWS Glue Schema Registry`_)

1. The Lambda Functions
-----------------------------

First of all, you need to deploy the AWS Lambda Functions into your AWS Account in order to use them as CustomResources
in AWS CloudFormation. The reason we went for Lambda and Custom Resource vs new AWS Resources, is because you need access
to brokers and Schema registry, which might be private.

2. The CLI
----------------

The files in which you will define your ACLs, Topics and Schemas follow a strict JSON definition, to ensure that input
is conform and help ensure successful deployment.
When the CLI runs, it will generate a new CloudFormation template that will be what's used to define the resources.



.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage

.. toctree::
    :maxdepth: 1
    :caption: Information

   modules
   contributing
   authors
   history

Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. |PYPI_VERSION| image:: https://img.shields.io/pypi/v/cfn-kafka-admin.svg
        :target: https://pypi.python.org/pypi/cfn-kafka-admin

.. |PYPI_LICENSE| image:: https://img.shields.io/pypi/l/cfn-kafka-admin
    :alt: PyPI - License
    :target: https://github.com/compose-x/cfn-kafka-admin/blob/master/LICENSE

.. |PYPI_PYVERS| image:: https://img.shields.io/pypi/pyversions/cfn-kafka-admin
    :alt: PyPI - Python Version
    :target: https://pypi.python.org/pypi/cfn-kafka-admin

.. |PYPI_WHEEL| image:: https://img.shields.io/pypi/wheel/cfn-kafka-admin
    :alt: PyPI - Wheel
    :target: https://pypi.python.org/pypi/cfn-kafka-admin

.. |FOSSA| image:: https://app.fossa.com/api/projects/git%2Bgithub.com%2Fcompose-x%2Fcfn-kafka-admin.svg?type=shield

.. |CODE_STYLE| image:: https://img.shields.io/badge/codestyle-black-black
    :alt: CodeStyle
    :target: https://pypi.org/project/black/

.. |TDD| image:: https://img.shields.io/badge/tdd-pytest-black
    :alt: TDD with pytest
    :target: https://docs.pytest.org/en/latest/contents.html

.. |BDD| image:: https://img.shields.io/badge/bdd-behave-black
    :alt: BDD with Behave
    :target: https://behave.readthedocs.io/en/latest/

.. _AWS Glue Schema Registry: https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html
