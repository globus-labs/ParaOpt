from .base_optimizer import BaseOptimizer
import itertools
from sys import maxsize

from paropt.storage.entities import Parameter, ParameterConfig
import logging

logger = logging.getLogger(__name__)
class GridSearch(BaseOptimizer):
    def __init__(self, num_configs_per_param):
        """
        Class for evenly searching the parameter search space. Performs NO optimization.
        """
        self.max_outcome = -maxsize
        self.grid_parameter_configs = []
        self.num_configs_per_param = num_configs_per_param

        # check the number of steps of each parameter
        if any(self.num_configs_per_param) < 1:
            raise Exception("num_configs_per_param must be >= 1")

    def setExperiment(self, experiment):
        parameters = Parameter.parametersToDict(experiment.parameters)
        
        parameters_linearly_spaced_vals = []

        # parameter start from the lower bound to higher bound
        for idx, parameter in enumerate(experiment.parameters):
            ncpp = self.num_configs_per_param[idx]
            # step_size = (parameter.maximum - parameter.minimum) / (ncpp - 1)
            if ncpp == 1:
                step_size = 0
            else:
                step_size = (parameter.maximum - parameter.minimum) / (ncpp - 1)
            parameter_linearly_spaced_vals = [parameter.minimum + (i * step_size) for i in range(ncpp)]
            parameter_linearly_spaced_vals = reversed(parameter_linearly_spaced_vals)
            parameters_linearly_spaced_vals.append(parameter_linearly_spaced_vals)
        
        # get cartesian product of configs
        parameter_configs_product = itertools.product(*parameters_linearly_spaced_vals)
        # create collections of ParameterConfigs from config values
        for parameter_config_collection in parameter_configs_product:
            parameter_configs = []
            for parameter, value in zip(experiment.parameters, parameter_config_collection):
                parameter_configs.append(ParameterConfig(parameter=parameter, value=value))
            self.grid_parameter_configs.append(parameter_configs)

    def __iter__(self):
        return iter(self.grid_parameter_configs)
    
    def register(self, trial):
        if trial.outcome > self.max_outcome:
            self.max_outcome_parameters = trial.parameter_configs
            self.max_outcome = trial.outcome

    def getMax(self):
        return self.max_outcome_parameters, self.max_outcome