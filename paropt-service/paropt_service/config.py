import psycopg2.extras
import globus_sdk
import psycopg2
import os
import urllib.request

from parsl.launchers import SingleNodeLauncher
from parsl.channels import SSHInteractiveLoginChannel, LocalChannel
from parsl.providers import CobaltProvider, LocalProvider, AWSProvider
from parsl.config import Config
from parsl.executors import HighThroughputExecutor
from parsl.executors.ipp import IPyParallelExecutor
from parsl.executors.ipp_controller import Controller

in_production = True if os.getenv('PROD') != None else False
public_ip = os.getenv('PUBLIC_IP')

_domain = os.getenv('SERVER_DOMAIN')
SERVER_DOMAIN = _domain if _domain != None else f'{public_ip}:8080'

def getAWSConfig():
  return Config(
    executors=[
      HighThroughputExecutor(
        label='htex_local',
        address=public_ip,
        worker_port_range=(54000, 54050),
        interchange_port_range=(54051, 54100),
        cores_per_worker=1,
        max_workers=1,
        provider=AWSProvider(
          image_id='ami-0257427d05c8c18ac', # image with bio tools installed 
          worker_init='pip3 install git+https://git@github.com/chaofengwu/paropt',
          region='us-east-2',
          key_name='aws_test',
          state_file='/etc/awsproviderstate.json',
          nodes_per_block=1,
          init_blocks=1,
          max_blocks=1,
          min_blocks=0,
          walltime='24:00:00',
        ),
      )
    ],
    strategy=None,
  )

GLOBUS_KEY = os.environ.get('globus_key')
# IMPORTANT: these client id's must NOT be None due to their use in auth checking
# This is why we set them to empty strings if missing
GLOBUS_CLIENT = os.environ.get('globus_client', '')
GLOBUS_CLIENT_NATIVE = os.environ.get('globus_client_native', '')

SECRET_KEY = os.environ.get('secret_key')

DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_NAME = os.environ.get('DB_NAME')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

_prod = in_production

def _get_db_connection():
  """
  Establish a database connection
  """
  con_str = "dbname={dbname} user={dbuser} password={dbpass} host={dbhost}".format(dbname=DB_NAME, dbuser=DB_USER,
                                                                                    dbpass=DB_PASSWORD, dbhost=DB_HOST)

  conn = psycopg2.connect(con_str)
  cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

  return conn, cur

def _load_funcx_client():
  """
  Create an AuthClient for the portal
  """
  # TODO: REMOVE THE TRUE
  if _prod or True:
      app = globus_sdk.ConfidentialAppAuthClient(GLOBUS_CLIENT,
                                                  GLOBUS_KEY)
  else:
      app = globus_sdk.ConfidentialAppAuthClient('', '')
  return app
