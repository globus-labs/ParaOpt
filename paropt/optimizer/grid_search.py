from .base_optimizer import BaseOptimizer
import itertools
from sys import maxsize

class GridSearch(BaseOptimizer):
  def __init__(self, command_params, num_configs_per_param):
    """
    Class for evenly searching the parameter search space. Does NOT implement optimization.
    """
    self.max_outcome = -maxsize
    self.grid_search_points = []
    self.command_params = command_params.copy() # copying to ensure dict not modifed while calculating points
    self.num_configs_per_param = num_configs_per_param

    ncpp = self.num_configs_per_param
    if ncpp < 2:
      raise Exception("num_configs_per_param must be >= 2")
    separate_parameter_configs = []
    for param, limits in self.command_params.items():
      min_val = limits[0]
      max_val = limits[1]
      step_size = (max_val - min_val) / (ncpp - 1)
      linearly_spaced_vals = [ min_val + (i * step_size) for i in range(ncpp) ]
      separate_parameter_configs.append(linearly_spaced_vals)
    # get cartesian product of param configs
    parameter_configs_product = itertools.product(*separate_parameter_configs)
    # convert sets into dictionaries
    parameter_names = [name for name, _ in self.command_params.items()]
    for parameter_config_collection in parameter_configs_product:
      self.grid_search_points.append(dict(zip(parameter_names, parameter_config_collection)))

  def __iter__(self):
    return iter(self.grid_search_points)
  
  def register(self, parameters, result):
    outcome = result[2]
    if outcome > self.max_outcome:
      self.max_outcome_parameters = parameters
      self.max_outcome = outcome

  def getMax(self):
    return self.max_outcome_parameters, self.max_outcome