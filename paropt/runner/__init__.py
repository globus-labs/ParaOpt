from .parsl import ParslRunner

__all__ = [
  'ParslRunner',
  'RunConfig'
]

class RunConfig():
  """A wrapper for a run configuration

  This is the context provided to the runner function, what scripts to run etc.

  Parameters
  ----------
  command_script_content : str
    script that runs the tool
  experiment_dict : dict
    dictionary representation of the experiment being run
  setup_script_content : str
    (optional) script intended to be run before the main command script
  finish_script_content : str
    (optional) script intended to be run after the main command script
  """
  def __init__(self,
               command_script_content,
               experiment_dict,
               setup_script_content=None,
               finish_script_content=None):
    self.command_script_content = command_script_content
    self.experiment_dict = experiment_dict
    self.setup_script_content = setup_script_content
    self.finish_script_content = finish_script_content
