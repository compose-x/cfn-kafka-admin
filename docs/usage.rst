
.. meta::
    :description: CFN Kafka Admin
    :keywords: AWS, CloudFormation, Kafka, Topics, ACL, Schema

###############
How to use
###############

Before we start - Limitations
===============================

Before we start, some reminders on the limitations:

Topic names must be unique
---------------------------

Topic names in the cluster must be unique. So if you adopt to have one repository for different teams/users,
ensure to have a strong naming convention that will avoid collisions.

Some properties are not updatable
-----------------------------------

Some topic properties **can not** be updated, and others can, on condition.
The most common one is `cleanup.policy` which defaults to ``delete``. You **can not** change the value of this property
to anything else. Instead, you must delete the topic first and re-create it.

.. tip::

    To delete a topic via this tool, and re-create it, just comment it out, render, deploy, and un-comment it again
    with new settings.

Input and Configuration files definitions
============================================

The tool will accept a configuration file that will override various settings and inject it into the final CloudFormation
template.

Parameters
------------

.. jsonschema:: ../cfn_kafka_admin/specs/ews-kafka-parameters.json

Input and configuration
------------------------

.. jsonschema:: ../cfn_kafka_admin/specs/aws-cfn-kafka-admin-provider-schema.json

ACLs
------

.. jsonschema:: ../cfn_kafka_admin/specs/ews-kafka-acl.json

Topics
--------

.. jsonschema:: ../cfn_kafka_admin/specs/ews-kafka-topic.json

Schema
--------

Note that for schemas, this only works for topic name strategy. Resulting schemas will be ``${topic.name}-[key|value]``

.. jsonschema:: ../cfn_kafka_admin/specs/ews-kafka-schema.json
