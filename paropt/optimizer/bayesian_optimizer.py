import logging
from random import randint

from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction

from .base_optimizer import BaseOptimizer
from paropt.storage.entities import Parameter, ParameterConfig, Trial

logger = logging.getLogger(__name__)

MAX_RETRY_SUGGEST = 10

class BayesianOptimizer(BaseOptimizer):
    def __init__(self, n_init, n_iter, alpha=1e-6, kappa=2.5, utility=None, budget=None, converge_thres=None, converge_step=None):
# These parameters are initialized by the runner
        # updated by setExperiment()
        
        self.optimizer = None
        self.alpha = alpha
        self.kappa = kappa
        self.utility = utility if utility != None else UtilityFunction(kind="ucb", kappa=self.kappa, xi=0.0)

        self.experiment_id = None
        self.parameters_by_name = None
        self.n_init = n_init
        self.n_iter = n_iter
        self.budget = budget
        self.converge_thres = converge_thres
        self.converge_step = converge_step
        self.converge_step_count = 0
        self.stop_flag = False

        self.using_budget_flag = False # check whether the current trial use budget
        self.using_converge_flag = False # check whether the current tirl need to consider in convergence
        self.previous_trials = []
        self.n_initted = 0
        self.n_itered = 0
        self.previous_trials_loaded = False

        self.all_trials = []
        self.visited_config = {} # store a string of config, and value is the index in previous_trials
    
    def setExperiment(self, experiment):
        """
        This is called by the runner after the experiment is properly initialized
        """
        self.parameters_by_name = {parameter.name: parameter for parameter in experiment.parameters}
        self.optimizer = BayesianOptimization(
            f=None,
            pbounds=Parameter.parametersToDict(experiment.parameters),
            alpha=self.alpha,
            verbose=2,
            random_state=randint(1, 100),
        )
        self.experiment_id = experiment.id
        self.previous_trials = experiment.trials
    
    def _trialParamsToDict(self, trial):
        params_dict = {}
        for parameter_config in trial.parameter_configs:
            params_dict[parameter_config.parameter.name] = parameter_config.value
        return params_dict

    def _load(self):
        if self.previous_trials == []:
            return

        for trial in self.previous_trials:
            params_dict = self._trialParamsToDict(trial)
            logger.info(f'Registering: {params_dict}, {trial.outcome}')
            try:
                self.register(trial) # update optimizer all by wrapped register so that automatically update total_trials/previous_trials
                # self.optimizer.register(
                #   params=params_dict,
                #   target=trial.outcome
                # )
            except KeyError:
                logger.warning(
                    f"Config already registered, ignoring; config: {params_dict}, outcome: {trial.outcome}"
                )
    
    def _configDictToParameterConfigs(self, config_dict):
        """
        Given a dictionary of parameters configurations, keyed by parameter name, value is value,
        return an array of ParameterConfigs
        """
        parameter_configs = []
        for name, value in config_dict.items():
            param = self.parameters_by_name.get(name, None)
            if param == None:
                raise Exception('Parameter with name "{}" not found in optimizer'.format(name))
            # TODO: This should return ParameterConfig values with the proper type (e.g. int, float)
            parameter_configs.append(ParameterConfig(parameter=param, value=value))
        return parameter_configs

    def _parameterConfigToString(self, parameter_configs):
        """
        transfer parameter configuration into string for hash
        {A: 10, B: 100} ==> '#A#10#B#100'
        """
        cur_config = ''
        for key, value in ParameterConfig.configsToDict(parameter_configs).items():
            cur_config += f'#{key}#{value}'
        return cur_config

    def _update_visited_config(self, parameter_configs):
        """
        given a new parameter configuration, update the visited_config dictionary, save key (string) and value (int , index in all_trials)
        """
        cur_config = self._parameterConfigToString(parameter_configs)
        if cur_config in self.visited_config:
            logger.warning(f'trying to update seen configuration in bayesian_optimizer._update_visited_config, existing one is {self._trialParamsToDict(self.all_trials[self.visited_config[cur_config]])}, new one is {self._parameterConfigsToConfigDict(parameter_configs)}')

        else:
            self.visited_config[cur_config] = len(self.all_trials) - 1

    def _getTrialWithParameterConfigs(self, parameter_configs):
        """Given a list of parameter configs, it returns a trial from previous_trials or None if not found"""
        # TODO: this should check self.previous_trials to find a trial that used the provided configs
        # FIXME: This function is unimplemented, functionally acting like every parameter config is unique
        cur_config = self._parameterConfigToString(parameter_configs)
        if cur_config in self.visited_config:
            logger.warning(f'find existing trial in bayesian_optimizer._getTrialWithParameterConfigs, existing one is {self._trialParamsToDict(self.all_trials[self.visited_config[cur_config]])}, new one is {self._parameterConfigsToConfigDict(parameter_configs)}')
            return self.all_trials[self.visited_config[cur_config]]
        return None

    def _suggestUniqueParameterConfigs(self):
        """Returns an untested list of parameter configs
        This is used for handling integer values for configuration values
        Since the model can only suggest floats, if Parameters are of integer type we don't want to run
        another trial that tests the exact same set of configurations
        This function raises an exception if unable to find a new configuration
        The approach:
            - get a suggested configuration
            - if the set of configurations have NOT been used before return it
            - if the set of configurations have been used before,
                register the point and get another suggestion
        """
        config_dict = self.optimizer.suggest(self.utility)
        param_configs = self._configDictToParameterConfigs(config_dict)
        trial = self._getTrialWithParameterConfigs(param_configs)
        n_suggests = 0
        while trial != None and n_suggests < MAX_RETRY_SUGGEST:
            logger.info(f"Retrying suggest: Non-unique set of ParameterConfigs: {param_configs}")
            # This set of configurations have been used before
            # register a new trail with same outcome but with our suggested (float) values
            dup_trial = Trial(
                parameter_configs=param_configs,
                outcome=trial.outcome,
                run_number=trial.run_number,
                experiment_id=trial.experiment_id,
            )
            self.register(dup_trial)
            # get another suggestion from updated model
            config_dict = self.optimizer.suggest(self.utility)
            param_configs = self._configDictToParameterConfigs(config_dict)
            trial = self._getTrialWithParameterConfigs(param_configs)
            n_suggests += 1

        if n_suggests == MAX_RETRY_SUGGEST:
            logger.warning(f'Meet maximum retry suggest {MAX_RETRY_SUGGEST}')
            raise Exception(f"BayesOpt failed to find untested config after {n_suggests} attempts. "
                                            f"Consider increasing the utility function kappa value")
        return param_configs
    
    def _parameterConfigsToConfigDict(self, parameter_configs):
        return {config.parameter.name: config.value for config in parameter_configs}

    def __iter__(self):
        return self
    
    def __next__(self):
        """
        Returns configs in this order
        1. random configs, n_init times
        2. suggested configs, n_iter times (after register configs into model)
        """
        if self.stop_flag:
            raise StopIteration
        else:
            if self.n_initted < self.n_init:
                self.n_initted += 1
                config_dict = self.optimizer.suggest(self.utility)
                next_config = self._configDictToParameterConfigs(config_dict)
                self.using_budget_flag = True
                self.using_converge_flag = False
                return next_config
            if not self.previous_trials_loaded:
                self.using_budget_flag = False
                self.using_converge_flag = False
                self.previous_trials_loaded = True
                self._load()
            if self.n_itered < self.n_iter:
                self.n_itered += 1
                next_config = self._suggestUniqueParameterConfigs()
                self.using_budget_flag = True
                self.using_converge_flag = True
                return next_config
            else:
                raise StopIteration
    

    def _update_converge(self, trial):
        best_param, best_out = self.getMax()
        if trial.outcome / best_out <= self.converge_thres:
            self.converge_step_count = 0
        else:
            self.converge_step_count += 1
        
        if self.converge_step_count >= self.converge_step:
            logger.exception(f'Meet creteria of converging')
            return -1
        else:
            return 0


    def _update_budget(self, trial):
        self.budget -= -trial.outcome*86400 # count in second
        if self.budget <= 0:
            logger.exception(f'Reach budget')
            return -1
        else:
            return 0


    def register(self, trial):
        """
        If previous trials have not been loaded, store result in previous trials to allow
        the init samples to be truly random. If they have been loaded, we can immediately register
        the result into the model.
        """
        # save to all trials and update visited_config dictionary
        self.all_trials.append(trial)
        self._update_visited_config(self._configDictToParameterConfigs(self._trialParamsToDict(trial)))
        if not self.previous_trials_loaded:
            self.previous_trials.append(trial)
            return
        
        if self.using_budget_flag and self.budget is not None:
            return_code = self._update_budget(trial)
            if return_code == -1:
                self.stop_flag = True

        if self.using_converge_flag and self.converge_thres is not None and self.converge_step is not None:
            return_code = slef._update_converge(trial)
            if return_code == -1:
                self.stop_flag = True

        self.optimizer.register(
            params=self._parameterConfigsToConfigDict(trial.parameter_configs),
            target=trial.outcome,
        )
        




    def getMax(self):
        return self.optimizer.max