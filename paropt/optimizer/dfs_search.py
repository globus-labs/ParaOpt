import logging
import numpy as np
from random import randint

from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction

from .base_optimizer import BaseOptimizer
from paropt.storage.entities import Parameter, ParameterConfig, Trial

from sys import maxsize

logger = logging.getLogger(__name__)

MAX_RETRY_SUGGEST = 10

class DFSSearchOptimizer():
    def __init__(self, pbounds, random_seed=None):
        self.pbounds = pbounds
        self.random_seed = random_seed
        self.max_outcome = -maxsize
        self.max_outcome_parameters = None

    def suggest(self):
        suggested_dict = {name: np.random.uniform(low=ran[0], high=ran[1]) for name, ran in self.pbounds.items()}
        return suggested_dict

    def register(self, trial):
        """
        update best
        """
        if trial.outcome > self.max_outcome:
            self.max_outcome_parameters = trial.parameter_configs
            self.max_outcome = trial.outcome

    def max(self):
        return self.max_outcome_parameters, self.max_outcome


class DFSSearch(BaseOptimizer):
	def __init__(self):
		pass