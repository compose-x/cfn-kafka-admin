
.. meta::
    :description: CFN Kafka Admin
    :keywords: AWS, CloudFormation, Kafka, Topics, ACL, Schema

##############################
The AWS Lambda Functions
##############################

Via AWS SAR
=============

You can find these Lambda Functions in `AWS Serverless Repository`_.

Manual install
===================

Pre-requisites
---------------

* Have an AWS Account and configure your client to have S3 and CloudFormation permissions access
* Have a S3 bucket to store the functions code into
* Have python3.7+ installed on your machine
* Have the AWS CLI (preferably v2) installed
* Clone the repository locally.
* Have a Kafka Admin set of credentials stored in AWS Secrets Manager or AWS SSM (avoid plaintext in configuration).

.. note::

    This guide was made for Linux/MacOS users.
    No Windows native support will be provided. Sorry for the inconvenience

Deploy the functions
---------------------

For the following, we are going to consider that the S3 bucket for the lambda code is called ``lambda-functions-code``

Now we run the following commands

.. code-block:: bash


    # Prepare our dependencies
    cd cfn-kafka-admin/
    python3 -m venv venv
    source venv/bin/activate
    pip install pip poetry -U
    poetry install

    # Build the function layout/layer

    make package

    # Upload to S3 and render output template

    aws cloudformation package --template-file .install/layer-macro-sar.yaml --s3-bucket lambda-functions-code \
    --s3-prefix cfn-kafka-admin --use-json --output-template-file functions.template

    # Deploy to CloudFormation

    aws cloudformation deploy --template-file functions.template --stack-name lambda-fn--cfn-kafka-admin \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
    --parameter-overrides VpcId=<vpc-id> Subnets=<subnet-1,subnet-2> KafkaSecretsArns=<arn_of_kafka_admin_secret>

.. _AWS Serverless Repository:
