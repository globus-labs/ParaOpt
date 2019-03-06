from parsl.app.app import python_app

@python_app
def timeCmd(cmd_script_path):
  import os
  import subprocess
  import time

  start_time = time.time()
  proc = subprocess.Popen(['bash', cmd_script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  outs, errs = proc.communicate()
  total_time = time.time() - start_time
  # invert b/c our optimizer is maximizing
  total_time = -total_time
  # divide by number of seconds in a day to scale down
  total_time = total_time / 86400
  return (proc.returncode, outs.decode(), total_time)
