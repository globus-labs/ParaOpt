import logging

from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction

from .base_optimizer import BaseOptimizer
from random import randint

logger = logging.getLogger(__name__)

class BayesianOptimizer(BaseOptimizer):
  def __init__(self, command_params, n_init, n_iter, utility=None, storage=None):
    self.optimizer = BayesianOptimization(
      f=None,
      pbounds=command_params,
      verbose=2,
      random_state=randint(1, 100),
    )
    if utility == None:
      self.utility = UtilityFunction(kind="ucb", kappa=2.5, xi=0.0)
    else:
      self.utility = utility

    self.n_init = n_init
    self.n_iter = n_iter
    self.storage = storage

    self.n_initted = 0
    self.n_itered = 0
    self.storage_loaded = False
  
  def _trialParamsToDict(self, trial):
    params_dict = {}
    for parameter_config in trial.parameter_configs:
      params_dict[parameter_config.parameter.name] = parameter_config.value
    return params_dict

  def _load(self):
    if self.storage == None:
      return
      # raise Exception('Unable to load into model, no storage set')
    previous_trials = self.storage.getPreviousTrials()
    for trial in previous_trials:
      params_dict = self._trialParamsToDict(trial)
      logger.info(f'Registering: {params_dict}, {trial.outcome}')
      self.optimizer.register(
        params=params_dict,
        target=trial.outcome
      )
  
  def __iter__(self):
    return self
  
  def __next__(self):
    if self.n_initted < self.n_init:
      self.n_initted += 1
      return self.optimizer.suggest(self.utility)
    if not self.storage_loaded:
      self.storage_loaded = True
      self._load()
    if self.n_itered < self.n_iter:
      self.n_itered += 1
      return self.optimizer.suggest(self.utility)
    else:
      raise StopIteration
  
  def register(self, params, result):
    self.optimizer.register(
      params=params,
      target=result[2],
    )
  
  def getMax(self):
    return self.optimizer.max