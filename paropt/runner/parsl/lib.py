from parsl.app.app import python_app

@python_app
def timeCommand(runConfig):
  import os
  import subprocess
  import time

  # run setup script
  if runConfig.setup_script_content != None:
    setup_script_path = 'setupCmd_{}'.format(time.time())
    with open(setup_script_path, 'w') as f:
      f.write(runConfig.setup_script_content)
    proc = subprocess.Popen(['bash', setup_script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    outs, errs = proc.communicate()
    if proc.returncode != 0:
      err_msg = f'Failed to run setupscript: \n{outs.decode()}'
      return (proc.returncode, err_msg, 0)
  
  # time command script
  cmd_script_path = 'timeCmd_{}'.format(time.time())
  with open(cmd_script_path, 'w') as f:
    f.write(runConfig.command_script_content)
  start_time = time.time()
  proc = subprocess.Popen(['bash', cmd_script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  outs, errs = proc.communicate()
  total_time = time.time() - start_time
  # invert b/c our optimizer is maximizing
  total_time = -total_time
  # divide by number of seconds in a day to scale down
  total_time = total_time / 86400
  return (proc.returncode, outs.decode(), total_time)
