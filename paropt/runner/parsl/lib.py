from parsl.app.app import python_app

@python_app
def timeCmd(script_content):
  import os
  import subprocess
  import time
  
  # write the script to a local file
  cmd_script_path = 'timeCmd_{}'.format(time.time())
  with open(cmd_script_path, 'w') as f:
    f.write(script_content)
  start_time = time.time()
  proc = subprocess.Popen(['bash', cmd_script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  outs, errs = proc.communicate()
  total_time = time.time() - start_time
  # invert b/c our optimizer is maximizing
  total_time = -total_time
  # divide by number of seconds in a day to scale down
  total_time = total_time / 86400
  return (proc.returncode, outs.decode(), total_time)
