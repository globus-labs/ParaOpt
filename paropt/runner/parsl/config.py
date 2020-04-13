import os
from socket import timeout
import urllib
from urllib.error import HTTPError, URLError
import logging

from parsl.config import Config
from parsl.executors import ThreadPoolExecutor, HighThroughputExecutor
from parsl.providers import AWSProvider, PBSProProvider
from parsl.launchers import MpiRunLauncher

from paropt.storage.entities import EC2Compute, LocalCompute, PBSProCompute

from parsl.addresses import address_by_interface
from parsl.monitoring.monitoring import MonitoringHub

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

      # get the required environment variables
      required_env_vars = ["PAROPT_AWS_REGION", "PAROPT_AWS_KEY_NAME", "PAROPT_AWS_STATE_FILE", "PAROPT_AWS_IAM_INSTANCE_PROFILE_ARN"]
      env_vars = {varname.replace('PAROPT_AWS_', '').lower(): os.getenv(varname) for varname in required_env_vars}
      missing_vars = [varname for varname, value in env_vars.items() if value == None]
      if missing_vars:
        raise Exception("Missing required environment variables for running parsl with AWS:\n{}".format(missing_vars))

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
              worker_init='pip3 install git+https://git@github.com/globus-labs/ParaOpt@Chaofeng_modification', # git+https://git@github.com/chaofengwu/paropt',#git+https://git@github.com/macintoshpie/paropt',
              nodes_per_block=1,
              init_blocks=1,
              max_blocks=1,
              min_blocks=0,
              walltime='24:00:00',
              spot_max_bid=2.0,
              **env_vars
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

  elif isinstance(compute, PBSProCompute):
    # NOTE: Assumes the paropt is being run on an PBS node with access to metadata service
    try:
      parsl_config = Config(
        executors=[
          HighThroughputExecutor(
            label="htex",
            heartbeat_period=15,
            heartbeat_threshold=120,
            worker_debug=True,
            max_workers=4,
            address=address_by_interface('ib0'),
            provider=PBSProProvider(
              launcher=MpiRunLauncher(),
              # PBS directives (header lines): for array jobs pass '-J' option
              # scheduler_options='#PBS -J 1-10',
              scheduler_options=compute.scheduler_options,
              # Command to be run before starting a worker, such as:
              # 'module load Anaconda; source activate parsl_env'.
              worker_init=compute.worker_init,
              # number of compute nodes allocated for each block
              nodes_per_block=1,
              min_blocks=1,
              max_blocks=5,
              cpus_per_node=compute.cpus_per_node,
              # medium queue has a max walltime of 24 hrs
              walltime=compute.walltime
            ),
          ),
        ],
        monitoring=MonitoringHub(
            hub_address=address_by_interface('ib0'),
            hub_port=55055,
            resource_monitoring_interval=10,
        ),
        strategy='simple',
        retries=3,
        app_cache=True,
        checkpoint_mode='task_exit'
      )

      return parsl_config
    except KeyError as e:
      logger.error('Failed initializing PBSPro config: {}'.format(e))
      raise e
  
  else:
    raise Exception('Unknown Compute type')