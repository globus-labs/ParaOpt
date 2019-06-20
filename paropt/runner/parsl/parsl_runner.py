import logging
import os
import time
import traceback
from string import Template

import parsl

from paropt import setFileLogger
from paropt.storage import LocalFile
from paropt.storage.entities import Trial, ParameterConfig
import paropt.runner
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

        self.run_result = {
            'success': True,
            'message': {}
        }
    
    def __repr__(self):
        return '\n'.join([
            f'ParslRunner(',
            f'    parsl_app={self.parsl_app!r}',
            f'    optimizer={self.optimizer!r}',
            f'    storage={self.storage!r}',
            f'    experiment={self.experiment!r}',
            f')\n'
        ])

    def _validateResult(self, params, res):
        if res['returncode'] != 0:
            raise Exception(f"Non-zero exit from trial:\n"
                                            f"    ParameterConfigs: {params}\n    Output: {res['stdout']}")

    def _writeScript(self, template, parameter_configs, file_prefix):
        """
        Format the template with provided parameter configurations and save locally for reference
        """
        script = Template(template).safe_substitute(ParameterConfig.configsToDict(parameter_configs))
        script_path = f'{self.templated_scripts_dir}/{file_prefix}_{self.experiment.tool_name}_{int(time.time())}.sh'
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
        # try:
        flag = True
        for idx, parameter_configs in enumerate(self.optimizer):
            try:
                logger.info(f'Writing script with configs {parameter_configs}')
                command_script_path, command_script_content = self._writeScript(self.command, parameter_configs, 'command')
                if self.experiment.setup_template_string != None:
                    _, setup_script_content = self._writeScript(self.experiment.setup_template_string, parameter_configs, 'setup')
                else:
                    setup_script_content = None
                if self.experiment.finish_template_string != None:
                    _, finish_script_content = self._writeScript(self.experiment.finish_template_string, parameter_configs, 'finish')
                else:
                    finish_script_content = None

                logger.info(f'Starting trial with script at {command_script_path}')
                runConfig = paropt.runner.RunConfig(
                    command_script_content=command_script_content,
                    experiment_dict=self.experiment.asdict(),
                    setup_script_content=setup_script_content,
                    finish_script_content=finish_script_content,
                )
                result = self.parsl_app(runConfig).result()
                self._validateResult(parameter_configs, result)
                trial = Trial(
                    outcome=result['run_time'],
                    parameter_configs=parameter_configs,
                    run_number=self.run_number,
                    experiment_id=self.experiment.id,
                )
                self.storage.saveResult(self.session, trial)
                self.optimizer.register(trial)
                self.run_result['success'] = True and self.run_result['success']
                flag = flag and self.run_result['success']
                self.run_result['message'] = (f'Successfully completed trials for experiment {self.experiment.id} run {self.run_number}, config is {parameter_configs}')

            except:
                logger.info(f'##################### 1\n')
                err_traceback = traceback.format_exc()
                trial = Trial(
                    outcome=10000000,
                    parameter_configs=parameter_configs,
                    run_number=self.run_number,
                    experiment_id=self.experiment.id,
                )
                logger.info(f'##################### 2\n')
                self.storage.saveResult(self.session, trial)
                logger.info(f'##################### 3\n')
                self.run_result['success'] = False
                self.run_result['message'] = (f'Failed to complete trials, experiment {self.experiment.id} run {self.run_number}, config is {parameter_configs}:\nError: {e}\n{err_traceback}')
                # config_dic = {config.parameter.name: config.value for config in parameter_configs}
                # logger.info(config)
                logger.info(f'##################### 4\n')
                logger.exception(err_traceback)
                logger.info(f'##################### 5\n')
            
        # except Exception as e:
        #     err_traceback = traceback.format_exc()
        #     self.run_result['success'] = False
        #     self.run_result['message'] = (f'Failed to complete trials, experiment {self.experiment.id} '
        #                                                                 f'run {self.run_number}:\nError: {e}\n{err_traceback}')
        # logger.exception(err_traceback)
        logger.info(f'Finished; Run result: {self.run_result}')
    
    def cleanup(self):
        """Cleanup DFK and parsl"""
        logger.info('Cleaning up parsl DFK')
        self._dfk.cleanup()
        parsl.clear()
    
    def getMax(self):
        return self.optimizer.getMax()
