import os
from socket import timeout
import urllib
from urllib.error import HTTPError, URLError
import logging
import configparser

from parsl.config import Config
from parsl.executors import ThreadPoolExecutor, HighThroughputExecutor
from parsl.providers import AWSProvider

from paropt.storage.entities import EC2Compute, LocalCompute

logger = logging.getLogger(__name__)

def getAWSPublicIP():
  """Fetch Public IP using metadata service"""
  return urllib.request.urlopen(
      url="http://169.254.169.254/latest/meta-data/public-ipv4",
      timeout=5
    ).read().decode()

def parslConfigFromCompute(compute):
  """Given a Compute instance, return a setup parsl configuration"""
  if isinstance(compute, EC2Compute):
    # NOTE: Assumes the paropt is being run on an EC2 instance with access to metadata service
    try:
      public_ip = getAWSPublicIP()

      paropt_config_path = os.path.expanduser('~/.paropt/config')
      paropt_config = configparser.ConfigParser()
      paropt_config.read(paropt_config_path)

      parsl_config = Config(
        executors=[
          HighThroughputExecutor(
            label='htex_local',
            address=public_ip,
            worker_port_range=(54000, 54050),
            interchange_port_range=(54051, 54100),
            cores_per_worker=1,
            max_workers=1,
            provider=AWSProvider(
              image_id=compute.ami,
              instance_type=compute.instance_model,
              worker_init='pip3 install git+https://git@github.com/macintoshpie/paropt',
              region=paropt_config['aws']['region'],
              key_name=paropt_config['aws']['key_name'],
              state_file=paropt_config['aws']['state_file'],
              nodes_per_block=1,
              init_blocks=1,
              max_blocks=1,
              min_blocks=0,
              walltime='01:00:00',
            ),
          )
        ],
        strategy=None,
      )

      return parsl_config
    except KeyError as e:
      logger.error('Failed initializing aws config: {}'.format(e))
      raise e
    except (HTTPError, URLError, OSError) as e:
      logger.error('Request to metadata service failed: {}'.format(e))
      raise e

  elif isinstance(compute, LocalCompute):
    return Config(
      executors=[
        ThreadPoolExecutor(
          max_threads=8,
          label='local_threads'
        )
      ]
    )
  
  else:
    raise Exception('Unknown Compute type')