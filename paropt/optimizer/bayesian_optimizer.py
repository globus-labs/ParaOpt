import logging
from random import randint

from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction

from .base_optimizer import BaseOptimizer
from paropt.storage.entities import Parameter, ParameterConfig, Trial

logger = logging.getLogger(__name__)

MAX_RETRY_SUGGEST = 10

class BayesianOptimizer(BaseOptimizer):
    def __init__(self, n_init, n_iter, alpha=1e-6, kappa=2.5, utility=None, budget=None, converge_thres=None, converge_steps=None):
        """
        Class  for using Bayesian Optimizer

        Parameters:
        ----------------
        n_init: int
            the number of initial trials
        n_iter: int
            the number of trials after initial trials
        alpha: float
            parameter for bayesian optimization
        kappa: float
            parameter for 'ucb' utility function
        utility (in progress): string
            utility function to use. default is 'ucb'
        budget: int
            a time budget counted in second. next trial will not be performed if running time has excessed the budget. currently the budget can only be used with timeCmd function. 
        converge_thres: float
            a threshold to determine whether to continue next trials. to continue, current_trial_outcome / best_outcome_up_to_now <= converge_thres. work together with converge_steps.
        converge_steps: int
            the number of steps to stop the experiment. If for converge_steps steps, the converge_thres creteria is not satisfied, the experiment will be ceased.
        """
        # These parameters are initialized by the runner
        # updated by setExperiment()
        
        self.optimizer = None
        if alpha is None:
            self.alpha = 1e-6
        else:
            self.alpha = alpha
        if kappa is None:
            self.kappa = 2.5
        else:
            self.kappa = kappa
            
        self.utility = utility if utility != None else UtilityFunction(kind="ucb", kappa=self.kappa, xi=0.0)

        self.experiment_id = None
        self.parameters_by_name = None
        self.n_init = n_init
        self.n_iter = n_iter
        self.budget = budget
        self.converge_thres = converge_thres
        self.converge_steps = converge_steps
        self.converge_steps_count = 0
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
        """
        load previous trial
        """
        if self.previous_trials == []:
            return

        for trial in self.previous_trials:
            params_dict = self._trialParamsToDict(trial)
            logger.info(f'Registering: {params_dict}, {trial.outcome}\n')
            if trial.outcome == 10000000:
                logger.info(f'Skip error trial\n')
                continue
            try:
                self.register(trial) # update optimizer all by wrapped register so that automatically update total_trials/previous_trials
            except KeyError:
                logger.warning(
                    f"Config already registered, ignoring; config: {params_dict}, outcome: {trial.outcome}\n"
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
            logger.warning(f'trying to update seen configuration in bayesian_optimizer._update_visited_config, existing one is {self._trialParamsToDict(self.all_trials[self.visited_config[cur_config]])}, new one is {self._parameterConfigsToConfigDict(parameter_configs)}\n')

        else:
            self.visited_config[cur_config] = len(self.all_trials) - 1

    def _getTrialWithParameterConfigs(self, parameter_configs):
        """Given a list of parameter configs, it returns a trial from previous_trials or None if not found"""
        cur_config = self._parameterConfigToString(parameter_configs)
        if cur_config in self.visited_config:
            logger.warning(f'find existing trial in bayesian_optimizer._getTrialWithParameterConfigs, existing one is {self._trialParamsToDict(self.all_trials[self.visited_config[cur_config]])}, new one is {self._parameterConfigsToConfigDict(parameter_configs)}\n')
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
        trial = self._getTrialWithParameterConfigs(param_configs) # trial is None if no existing trial with same parameters
        n_suggests = 0
        while trial != None and n_suggests < MAX_RETRY_SUGGEST:
            # This set of configurations have been used before
            # register a new trail with same outcome but with our suggested (float) values
            
            self.using_budget_flag = False # this register does not count in budget
            
            dup_trial = Trial(
                parameter_configs=param_configs,
                outcome=trial.outcome,
                run_number=trial.run_number,
                experiment_id=trial.experiment_id,
                obj_parameters=trial.obj_parameters,
            )

            self.register(dup_trial) # register this trial

            # get another suggestion from updated model, and check
            config_dict = self.optimizer.suggest(self.utility)
            param_configs = self._configDictToParameterConfigs(config_dict)
            trial = self._getTrialWithParameterConfigs(param_configs)
            n_suggests += 1

        if n_suggests == MAX_RETRY_SUGGEST:
            logger.warning(f'Meet maximum retry suggest {MAX_RETRY_SUGGEST}\n')
            raise Exception(f"BayesOpt failed to find untested config after {n_suggests} attempts. Consider increasing the utility function kappa value.\n")
        self.using_budget_flag = True
        return param_configs
    
    def _parameterConfigsToConfigDict(self, parameter_configs):
        return {config.parameter.name: config.value for config in parameter_configs}

    def __iter__(self):
        return self
    
    def __next__(self):
        """
        Returns configs in this order
        1. random configs, n_init times
        2. load previous trials
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
        """
        update the converge steps
        """
        best_out = self.getMax()
        # current_outcome/best_outcome <= converget_thres
        if trial.outcome / float(best_out['target']) <= self.converge_thres:
            self.converge_steps_count = 0
        else:
            self.converge_steps_count += 1
        
        if self.converge_steps_count >= self.converge_steps:
            logger.exception(f'Meet creteria of converging\n')
            return -1
        else:
            return 0


    def _update_budget(self, trial):
        """
        update budget
        """
        self.budget -= -trial.outcome*86400 # count in second
        if self.budget <= 0:
            logger.exception(f'Reach budget\n')
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
        
        
        if self.using_budget_flag and self.budget is not None:
            return_code = self._update_budget(trial)
            if return_code == -1:
                self.stop_flag = True

        if self.using_converge_flag and self.converge_thres is not None and self.converge_steps is not None:
            return_code = self._update_converge(trial)
            if return_code == -1:
                self.stop_flag = True

        if not self.previous_trials_loaded:
            self.previous_trials.append(trial)
            return
        self.optimizer.register(
            params=self._parameterConfigsToConfigDict(trial.parameter_configs),
            target=trial.outcome,
        )
        




    def getMax(self):
        return self.optimizer.max