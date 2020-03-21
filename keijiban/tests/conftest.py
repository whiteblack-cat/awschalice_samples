import pytest

from moto import mock_dynamodb2
import boto3

mock_dy = mock_dynamodb2()
mock_dy.start()
from init import init
init('keijiban')

from app import app as chalice_app


@pytest.fixture
def app():
    return chalice_app

