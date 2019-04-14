import logging
import os
import time
import traceback
from string import Template

import parsl

from paropt import setFileLogger
from paropt.storage import LocalFile
from paropt.storage.entities import Trial, ParameterConfig

logger = logging.getLogger(__name__)

class ParslRunner:
  def __init__(self,
              parsl_config,
              parsl_app,
              optimizer,
              storage=None,
              experiment=None):

    self.parsl_config = parsl_config
    self.parsl_app = parsl_app
    self._dfk = None
    self.optimizer = optimizer
    self.storage = storage if storage != None else LocalFile()
    self.session = storage.Session()

    self.experiment, last_run_number, _ = storage.getOrCreateExperiment(self.session, experiment)
    self.run_number = last_run_number + 1
    self.optimizer.setExperiment(self.experiment)
    self.command = experiment.command_template_string

    # setup paropt info directories
    self.paropt_dir = f'./optinfo'
    if not os.path.exists(self.paropt_dir):
      os.mkdir(self.paropt_dir)

    run_number = 0
    self.run_dir = f'{self.paropt_dir}/exp_{self.experiment.id:03}/{self.run_number:03}'
    if os.path.exists(self.run_dir):
      raise Exception(f'{self.run_dir} already exists, '
                       'cannot continue with inconsistency between database and local run info')
    os.makedirs(self.run_dir)

    self.templated_scripts_dir = f'{self.run_dir}/templated_scripts'
    os.mkdir(self.templated_scripts_dir)

    setFileLogger(f'{self.run_dir}/paropt.log')

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
    try:
      for parameter_configs in self.optimizer:
        logger.info(f'Writing script with configs {parameter_configs}')
        script_path, script_content = self._writeScript(parameter_configs)
        # TODO: add user hook for customization
        # Hook should take in tool param configuration and current parsl configuration as arguments
        # Hook should return a new parsl configuration if it needs to be changed, or None if not
        # self.prerun_hook(config, self.parsl_config)
        logger.info(f'Starting trial with script at {script_path}')
        result = self.parsl_app(script_content).result()
        self._validateResult(parameter_configs, result)
        trial = Trial(
          outcome=result[2],
          parameter_configs=parameter_configs,
          run_number=self.run_number,
          experiment_id=self.experiment.id
        )
        self.storage.saveResult(self.session, trial)
        self.optimizer.register(trial)
    except Exception as e:
      logger.info('Whoops, something went wrong... {e}')
      logger.exception(traceback.format_exc())
    logger.info('Finished running tasks')
  
  def cleanup(self):
    """Cleanup DFK and parsl"""
    logger.info('Cleaning up parsl DFK')
    self._dfk.cleanup()
    parsl.clear()
  
  def getMax(self):
    return self.optimizer.getMax()
