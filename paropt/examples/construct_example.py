import os

import paropt
from paropt.runner import ParslRunner
from paropt.storage import RelationalDB
from paropt.optimizer import BayesianOptimizer, GridSearch, RandomSearch
from paropt.runner.parsl import timeCmd, searchMatrix, variantCallerAccu
from paropt.storage.entities import Parameter, PARAMETER_TYPE_INT, PARAMETER_TYPE_FLOAT, Experiment, LocalCompute, EC2Compute, PBSProCompute
import json
import sys

# set up logger
paropt.setConsoleLogger()

# commands that for setup
setup_template_string = """
conda activate paropt
"""
# commands that for run. need include the parameter name for substitution
command_template_string = """
#! /bin/bash
sleep ${myParam}
sleep ${myParamB}
sleep ${myParamC}
"""
# commands that for finishing the experiment
finish_template_string = """
conda deactivate
"""

# the name, type, and range for parameters to search
parameters = [
        Parameter(name="myParam", type=PARAMETER_TYPE_INT, minimum=5, maximum=10),
        Parameter(name="myParamB", type=PARAMETER_TYPE_FLOAT, minimum=3, maximum=5),
        Parameter(name="myParamC", type=PARAMETER_TYPE_INT, minimum=3, maximum=5)
        ]

# define compute type
# run on PBS
PBS_compute = PBSProCompute(cpus_per_node=1, walltime='1:00:00', scheduler_options='#PBS -P 11001079\n#PBS -l select=1:mem=1G\n#PBS -N PBSPro_paraopt_test', worker_init='module load openmpi\nsource activate paropt')

# run on AWS (need a server to run paraopt_service, and submit experiment via paropat_sdk)
AWS_compute = EC2Compute(instance_family='c5', instance_model='c5.2xlarge', ami='XXXXXXX')

# run locally
LOCAL_compute = LocalCompute(max_threads=8)

# define experiment entity
experiment_inst = Experiment(
    tool_name='test_script',
    parameters=parameters,
    command_template_string=command_template_string,
    setup_template_string=setup_template_string,
    finish_template_string=finish_template_string,
    compute=LOCAL_compute
)

# define the storage
# when run on the server, this doesn't change - we always connect to an AWS RDS postgres database
# When running locally you can just use a sqlite database like below. The last argument is the database name
# so you could test a blank slate by just changing the name or deleting the old liteTest.db file.

LOCAL_storage = RelationalDB(
    'sqlite',
    '',
    '',
    '',
    'liteTest',
)

# need to define these DB related parameters
AWSRDS_storage = RelationalDB(
    'postgresql',
    DB_USER,
    DB_PASSWORD,
    DB_HOST,
    DB_NAME
)

# define optimizer
bayesian_optimizer = BayesianOptimizer(
    n_init=2,
    n_iter=1,
    alpha=1e-3,
    kappa=2.5, 
    utility='ucb', 
    budget=None, 
    converge_thres=None, 
    converge_steps=None
)

# search on 2*2*2 grid
grid_optimizer = GridSearch([2,2,2])


random_optimizer = RandomSearch(n_iter=10, 
    random_seed=None, 
    budget=None, 
    converge_thres=None, 
    converge_steps=None
)

coordinate_optimizer = CoordinateSearch(n_init=1, 
    n_iter=20, 
    random_seed=None, 
    budget=None, 
    converge_thres=None, 
    converge_steps=None\
)

# create parslrunner, and the objective function and objective function parameters
po = ParslRunner(
    obj_func=getattr(paropt.runner.parsl, "timeCmd"),
    obj_func_params={'timeout': 15},
    optimizer=optimizer,
    storage=storage,
    experiment=experiment_inst,
    logs_root_dir='./myTestLogs')

po.run()
