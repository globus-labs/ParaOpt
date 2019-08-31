#!/usr/bin/env python3

import os
import yaml
import json
import sys
import argparse
import time

from globus_sdk.response import GlobusHTTPResponse

from paropt_sdk.client import ParoptClient

FILE_TYPE_MSG = 'Files provided must end with .yaml, .yml, or .json'
SECONDS_IN_DAY = 86400
MAX_FAILS = 3

def printResponse(response: GlobusHTTPResponse):
  """Prints basic response info"""
  try:
    response_body = json.dumps(response.data, indent=2)
  except ValueError:
    response_body = response.text

  print(f'status code:\n  {response.http_status}\n'
        f'response body:\n  {response_body}')

def httpOK(response: GlobusHTTPResponse) -> bool:
  """Determines if response status code is in ok range"""
  return 200 <= response.http_status <= 299

def waitForJob(po: ParoptClient, job_id: str, max_wait: int, sleep_interval=1) -> bool:
  """Wait for job to finish. Raises exception if timesout or fails to get response too many times

  Parameters
  ----------
  po : ParoptClient
    instance of service api
  job_id : str
    id of job
  max_wait : int
    maximum number of minutes to wait. If negative, will wait for 24 hours
  sleep_interval : int
    minutes to sleep between checks if the job is finished
  
  Returns
  -------
  success : bool
  """
  if max_wait < 0:
    timeout = time.time() + SECONDS_IN_DAY
  else:
    timeout = time.time() + (max_wait * 60)
  # convert sleep interval to seconds
  sleep_interval_secs = sleep_interval * 60
  n_fails = 0

  while time.time() < timeout and n_fails < MAX_FAILS:
    print(f"Job running, going to sleep for {sleep_interval} minutes...")
    time.sleep(sleep_interval_secs)
    job_res = po.getJob(job_id)
    if job_res.http_status == 200:
      job_data = job_res.data.get('job', {})
      job_status = job_data.get('job_status')
      if job_status == 'finished':
        return True
      elif job_status == 'failed':
        raise Exception(f'Server failed to run trials. See error info below (from server):\n'
                        f'{job_data.get("job_exc_info", "")}'.replace('\n', '\n| '))
      else:
        # still running
        continue
    else:
      # something unexpected happened
      n_fails += 1
      print("WARNING: Unexpected response:")
      printResponse(job_res)
      continue
  
  # failed to finish job in max time or too many fails occurred
  if n_fails == MAX_FAILS:
    raise Exception("Failed to wait for job: Too may failed calls/responses to api")
  else:
    raise Exception("Failed to wait for job: Reached maximum timeout")

def loadYmlJson(file_path: str):
  """Get the given json or yaml file as a dict"""
  with open(file_path) as f:
    if file_path.endswith('.yaml') or file_path.endswith('.yml'):
      return yaml.load(f)
    elif file_path.endswith('.json'):
      return json.loads(f.read())
    else:
      return None

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Python cli for interacting with paropt service')
  parser.add_argument('--experiment',
                      type=str,
                      required=True,
                      help='path to experiment yaml or json')
  parser.add_argument('--optimizer',
                      type=str,
                      required=True,
                      help='path to optimizer experiment or json')
  parser.add_argument('--maxwait',
                      type=int,
                      default=0,
                      help='maximum time in minutes to wait for trial to finish; default is 0; < 0 waits forever')
  parser.add_argument('--sleepdur',
                      type=int,
                      default=1,
                      help='determines polling interval in minutes when maxwait != 0')
  args = parser.parse_args()

  # get experiment data
  experiment = loadYmlJson(args.experiment)
  if experiment == None:
    print(FILE_TYPE_MSG)
    sys.exit(1)
  
  # get optimizer data
  optimizer = loadYmlJson(args.optimizer)
  if optimizer == None:
    print(FILE_TYPE_MSG)
    sys.exit(1)
  
  try:
    print("\n---- Creating client ----")
    po = ParoptClient()

    print("\n---- Creating/getting experiment ----")
    exp_res = po.getOrCreateExperiment(experiment)
    printResponse(exp_res)
    if not httpOK(exp_res):
      raise Exception("Failed to create experiment (status code not ok)")
    exp_data = exp_res.data
    exp_id = exp_data.get('id')
    if not exp_id:
      raise Exception("Expected experiment response to contain 'id'")

    print("\n---- Running job ----")
    trial_res = po.runTrial(exp_id, optimizer)
    printResponse(trial_res)
    if not httpOK(trial_res):
      raise Exception("Failed to run trial:\n {}".format(trial_res.data))
    trial_data = trial_res.data
    submitted_job_id = trial_data.get('job', {}).get('job_id')
    
    print("\n---- Starting to wait for job to finish ----")
    if args.maxwait != 0:
      waitForJob(po, submitted_job_id, args.maxwait)
      print('Successfully ran trials for experiment')
    else:
      print("Max wait == 0, not waiting for job to finish...")
      
    print("\n---- Finished ----")

  except:
    print("\n---- Error ----")
    raise
