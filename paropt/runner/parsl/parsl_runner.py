import logging
import os
import time
import traceback
from string import Template

import parsl

from paropt import setFileLogger
from paropt.storage import LocalFile
from paropt.storage.entities import Trial, ParameterConfig
from paropt.optimizer import *
import paropt.runner
from paropt.runner.parsl.config import parslConfigFromCompute
from paropt.util.plot import GridSearch_plot

logger = logging.getLogger(__name__)

class ParslRunner:
    def __init__(self,
                obj_func,
                optimizer,
                obj_func_params=None, 
                storage=None,
                experiment=None,
                logs_root_dir='.',
                plot_info={'draw_plot': False, 'plot_dir': '.'}
                ):

        self.plot_info = plot_info
        self.obj_func = obj_func
        if obj_func_params is None:
            self.obj_func_params = {'timeout': 0}
        else:
            self.obj_func_params = obj_func_params
        self._dfk = None
        self.optimizer = optimizer
        self.storage = storage if storage != None else LocalFile()
        self.session = storage.Session()

        # get or create the experiment
        self.experiment, last_run_number, _ = storage.getOrCreateExperiment(self.session, experiment)
        self.run_number = last_run_number + 1
        self.optimizer.setExperiment(self.experiment)
        self.command = experiment.command_template_string

        self.plot_info['experiment_id'] = self.experiment.id

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
            f'    obj_func={self.obj_func!r}',
            f'    optimizer={self.optimizer!r}',
            f'    storage={self.storage!r}',
            f'    experiment={self.experiment!r}',
            f')\n'
        ])

    def _validateResult(self, params, res):
        if res['returncode'] != 0:
            raise Exception(f"Non-zero exit from trial:\n\tParameterConfigs: {params}\n\tOutput: {res['stdout']}")
        if res['stdout'] == 'Timeout':
            raise Exception(f"Timeout:\n\tParameterConfigs: {params}\n\tOutput: {res['stdout']}")

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

        flag = True
        initialize_flag = True
        result = None
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
                # set warm-up experiments 
                if initialize_flag:
                    initialize_flag = False
                    logger.info(f'Starting initializing trial with script at {command_script_path}')
                    runConfig = paropt.runner.RunConfig(
                        command_script_content=command_script_content,
                        experiment_dict=self.experiment.asdict(),
                        setup_script_content=setup_script_content,
                        finish_script_content=finish_script_content,
                    )
                    initializing_func_param = {}
                    for key, val in self.obj_func_params.items():
                        initializing_func_param[key] = val
                    initializing_func_param['timeout'] = 300
                    # result = self.obj_func(runConfig, **self.obj_func_params).result()
                    result = self.obj_func(runConfig, **initializing_func_param).result()


                logger.info(f'Starting trial with script at {command_script_path}')
                runConfig = paropt.runner.RunConfig(
                    command_script_content=command_script_content,
                    experiment_dict=self.experiment.asdict(),
                    setup_script_content=setup_script_content,
                    finish_script_content=finish_script_content,
                )
                result = None
                result = self.obj_func(runConfig, **self.obj_func_params).result()
                self._validateResult(parameter_configs, result)
                trial = Trial(
                    outcome=result['obj_output'],
                    parameter_configs=parameter_configs,
                    run_number=self.run_number,
                    experiment_id=self.experiment.id,
                    obj_parameters=result['obj_parameters'],
                )
                self.storage.saveResult(self.session, trial)
                self.optimizer.register(trial)
                self.run_result['success'] = True and self.run_result['success']
                flag = flag and self.run_result['success']
                self.run_result['message'][f'experiment {self.experiment.id} run {self.run_number}, config is {parameter_configs}'] = (f'Successfully completed trials {idx} for experiment')

            except Exception as e:
                err_traceback = traceback.format_exc()
                if result is not None and result['stdout'] == 'Timeout': # for timeCommandLimitTime in lib, timeout
                    trial = Trial(
                        outcome=result['obj_output'],
                        parameter_configs=parameter_configs,
                        run_number=self.run_number,
                        experiment_id=self.experiment.id,
                        obj_parameters=result['obj_parameters'],
                    )
                    self.optimizer.register(trial)
                    logger.exception(f'time out')
                    self.storage.saveResult(self.session, trial)
                    self.run_result['success'] = False
                    self.run_result['message'][f'experiment {self.experiment.id} run {self.run_number}, config is {parameter_configs}'] = (f'Failed to complete trials {idx}:\nError: {e}\n{err_traceback}')

                else:
                    trial = Trial(
                        outcome=10000000,
                        parameter_configs=parameter_configs,
                        run_number=self.run_number,
                        experiment_id=self.experiment.id,
                        obj_parameters={},
                    )
                    self.storage.saveResult(self.session, trial)
                    self.run_result['success'] = False
                    self.run_result['message'][f'experiment {self.experiment.id} run {self.run_number}, config is {parameter_configs}'] = (f'Failed to complete trials {idx}:\nError: {e}\n{err_traceback}')
        
        logger.info(f'Finished; Run result: {self.run_result}')
        if self.plot_info['draw_plot']:
            # session = db_storage.Session()
            try:
                trials = self.storage.getTrials(self.session, self.experiment.id)
                trials_dicts = [trial.asdict() for trial in trials]
            except:
                self.session.rollback()
                raise
            # finally:
            #     session.close()
            # return jsonify(trials), 200
            logger.info(f'res: {trials_dicts}')
            if isinstance(self.optimizer, GridSearch):
                ret = GridSearch_plot(trials_dicts, plot_info)
            else:
                logger.info(f'Unsupport type of optimizer for plot')

            if ret['success'] == False:
                logger.info(f'Error when generating plot: {ret["error"]}')
            else:
                logger.info(f'Successfully generating plot')
        else:
            logger.info(f'Skip generating plot')
    
    def cleanup(self):
        """Cleanup DFK and parsl"""
        logger.info('Cleaning up parsl DFK')
        self._dfk.cleanup()
        parsl.clear()
    
    def getMax(self):
        return self.optimizer.getMax()
