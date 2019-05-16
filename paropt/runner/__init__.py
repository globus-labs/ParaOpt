from .parsl import ParslRunner

__all__ = [
  'ParslRunner',
  'RunConfig'
]

class RunConfig():
  def __init__(self, command_script_content, experiment_dict, setup_script_content=None):
    self.command_script_content = command_script_content
    self.experiment_dict = experiment_dict
    self.setup_script_content = setup_script_content
