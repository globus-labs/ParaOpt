import logging
from random import randint

from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction

from .base_optimizer import BaseOptimizer
from paropt.storage.entities import Parameter, ParameterConfig

logger = logging.getLogger(__name__)

class BayesianOptimizer(BaseOptimizer):
  def __init__(self, n_init, n_iter, utility=None):
    # These parameters are initialized by the runner
    # updated by setExperiment()
    self.experiment_id = None
    self.parameters_by_name = None
    self.optimizer = None
    self.previous_trials = []

    self.utility = utility if utility != None else UtilityFunction(kind="ucb", kappa=2.5, xi=0.0)
    self.n_init = n_init
    self.n_iter = n_iter

    self.n_initted = 0
    self.n_itered = 0
    self.previous_trials_loaded = False
  
  def setExperiment(self, experiment):
    """
    This is called by the runner after the experiment is properly initialized
    """
    self.parameters_by_name = {parameter.name: parameter for parameter in experiment.parameters}
    self.optimizer = BayesianOptimization(
      f=None,
      pbounds=Parameter.parametersToDict(experiment.parameters),
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
        self.optimizer.register(
          params=params_dict,
          target=trial.outcome
        )
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
      parameter_configs.append(ParameterConfig(parameter=param, value=value))
    return parameter_configs
  
  def _parameterConfigsToConfigDict(self, parameter_configs):
    return {config.parameter.name: config.value for config in parameter_configs}

  def __iter__(self):
    return self
  
  def __next__(self):
    """
    Returns
    1. fits fresh model until it's finished the init trials, then fits previous trials
    2. returns 
    """
    if self.n_initted < self.n_init:
      self.n_initted += 1
      config_dict = self.optimizer.suggest(self.utility)
      return self._configDictToParameterConfigs(config_dict)
    if not self.previous_trials_loaded:
      self.previous_trials_loaded = True
      self._load()
    if self.n_itered < self.n_iter:
      self.n_itered += 1
      config_dict =  self.optimizer.suggest(self.utility)
      return self._configDictToParameterConfigs(config_dict)
    else:
      raise StopIteration
  
  def register(self, trial):
    """
    If previous trials have not been loaded, store result in previous trials to allow
    the init samples to be truly random. If they have been loaded, we can immediately register
    the result into the model.
    """
    if not self.previous_trials_loaded:
      self.previous_trials.append(trial)
      return
    self.optimizer.register(
      params=self._parameterConfigsToConfigDict(trial.parameter_configs),
      target=trial.outcome,
    )

  def getMax(self):
    return self.optimizer.max