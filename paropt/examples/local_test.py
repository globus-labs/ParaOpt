import os

import paropt
from paropt.runner import ParslRunner
from paropt.storage import RelationalDB
from paropt.optimizer import BayesianOptimizer, GridSearch, RandomSearch
from paropt.runner.parsl import timeCmd, searchMatrix, variantCallerAccu
from paropt.storage.entities import Parameter, PARAMETER_TYPE_INT, PARAMETER_TYPE_FLOAT, Experiment, LocalCompute, EC2Compute, PBSProCompute
import json
import sys


paropt.setConsoleLogger()

# when running on server, the experiment is fetched first before doing anything
# if the experiment isn't found then running the trial fails
command_template_string = """
#! /bin/bash
sleep ${myParam}
sleep ${myParamB}
sleep ${myParamC}
"""

experiment_inst = Experiment(
  tool_name='anothertoolaaa',
  parameters=[
    Parameter(name="myParam", type=PARAMETER_TYPE_INT, minimum=5, maximum=10),
    Parameter(name="myParamB", type=PARAMETER_TYPE_INT, minimum=3, maximum=5),
    Parameter(name="myParamC", type=PARAMETER_TYPE_INT, minimum=3, maximum=5)
  ],
  command_template_string=command_template_string,
  # we use LocalCompute here b/c we don't want to launch jobs on EC2 like the server does
  compute=LocalCompute(max_threads=8)
)

# when run on the server, this doesn't change - we always connect to an AWS RDS postgres database
# When running locally you can just use a sqlite database like below. The last argument is the database name
# so you could test a blank slate by just changing the name or deleting the old liteTest.db file.
storage = RelationalDB(
  'sqlite',
  '',
  '',
  '',
  'liteTest',
)

# when run on server, this is determined by optimizer the user POSTs
optimizer = BayesianOptimizer(
  n_init=2,
  n_iter=1,
  alpha=1e-3
)
li = [2,2,2]
#optimizer = GridSearch(li)
#optimizer = RandomSearch(n_iter=10)
#optimizer = CoordinateSearch(n_iter=20)
# this is what runs it all 
po = ParslRunner(
  obj_func=getattr(paropt.runner.parsl, "timeCmd"),
  obj_func_params={'timeout': 15},
  optimizer=optimizer,
  storage=storage,
  experiment=experiment_inst,
  logs_root_dir='./myTestLogs')

po.run()
