import logging
import os
import time
import traceback
from string import Template

import parsl

from paropt import setFileLogger
from paropt.storage import LocalFile
from paropt.storage.entities import Trial, ParameterConfig
from paropt.runner.parsl.config import parslConfigFromCompute

logger = logging.getLogger(__name__)

class ParslRunner:
  def __init__(self,
              parsl_app,
              optimizer,
              storage=None,
              experiment=None,
              logs_root_dir='.'):

    self.parsl_app = parsl_app
    self._dfk = None
    self.optimizer = optimizer
    self.storage = storage if storage != None else LocalFile()
    self.session = storage.Session()

    # get or create the experiment
    self.experiment, last_run_number, _ = storage.getOrCreateExperiment(self.session, experiment)
    self.run_number = last_run_number + 1
    self.optimizer.setExperiment(self.experiment)
    self.command = experiment.command_template_string

    # setup compute
    self.compute = self.experiment.compute
    self.parsl_config = parslConfigFromCompute(self.compute)

    # setup paropt info directories
    self.paropt_dir = f'{logs_root_dir}/optinfo'
    if not os.path.exists(logs_root_dir):
      raise Exception(f'Logs directory does not exist: {logs_root_dir}')
    os.makedirs(self.paropt_dir, exist_ok=True)
    
    # setup directory and files for this run
    self.exp_run_dir = f'{self.paropt_dir}/exp_{self.experiment.id:03}/{self.run_number:03}'
    os.makedirs(self.exp_run_dir, exist_ok=True)
    setFileLogger(f'{self.exp_run_dir}/paropt.log')
    self.templated_scripts_dir = f'{self.exp_run_dir}/templated_scripts'

    # set parsl's logging directory
    self.parsl_config.run_dir = f'{self.exp_run_dir}/parsl'
    os.makedirs(self.templated_scripts_dir, exist_ok=True)
  
  def __repr__(self):
    return '\n'.join([
      f'ParslRunner(',
      f'  parsl_app={self.parsl_app!r}',
      f'  optimizer={self.optimizer!r}',
      f'  storage={self.storage!r}',
      f'  experiment={self.experiment!r}',
      f')\n'
    ])

  def _validateResult(self, params, res):
    if res[0] != 0:
      raise Exception("Non-zero exit from trial:\n  ParameterConfigs: {}\n  Output: {}".format(params, res[1]))

  def _writeScript(self, parameter_configs):
    """
    Format the template with provided parameter configurations and save locally for reference
    """
    script = Template(self.command).safe_substitute(ParameterConfig.configsToDict(parameter_configs))
    script_path = f'{self.templated_scripts_dir}/timeScript_{self.experiment.tool_name}_{int(time.time())}.sh'
    with open(script_path, "w") as f:
      f.write(script)
    return script_path, script
  
  def run(self, debug=False):
    """
    Run trials provided by the optimizer while saving results.
    """
    if debug:
      parsl.set_stream_logger()
    self._dfk = parsl.load(self.parsl_config)
    logger.info(f'Starting ParslRunner with config\n{self}')
    try:
      for parameter_configs in self.optimizer:
        logger.info(f'Writing script with configs {parameter_configs}')
        script_path, script_content = self._writeScript(parameter_configs)
        logger.info(f'Starting trial with script at {script_path}')
        result = self.parsl_app(script_content).result()
        self._validateResult(parameter_configs, result)
        trial = Trial(
          outcome=result[2],
          parameter_configs=parameter_configs,
          run_number=self.run_number,
          experiment_id=self.experiment.id,
        )
        self.storage.saveResult(self.session, trial)
        self.optimizer.register(trial)
    except Exception as e:
      logger.info('Whoops, something went wrong... {e}')
      logger.exception(traceback.format_exc())
    logger.info('Finished running tasks\n\n\n')
  
  def cleanup(self):
    """Cleanup DFK and parsl"""
    logger.info('Cleaning up parsl DFK')
    self._dfk.cleanup()
    parsl.clear()
  
  def getMax(self):
    return self.optimizer.getMax()
