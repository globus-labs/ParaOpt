#!/usr/bin/env python3
#### used for create experiment from yaml/json file

import os
import yaml
import json
import sys
import argparse
import time

import parsl
import paropt
from paropt.runner import ParslRunner
from paropt.storage import LocalFile, RelationalDB
from paropt.optimizer import BayesianOptimizer, GridSearch, RandomSearch, CoordinateSearch
from paropt.runner.parsl import *
from paropt.storage.entities import Parameter, Experiment, EC2Compute, LocalCompute, PBSProCompute


FILE_TYPE_MSG = 'Files provided must end with .yaml, .yml, or .json'
DB_DIALECT = 'sqlite'
DB_HOST = ''
DB_USER = ''
DB_PASSWORD = ''
DB_NAME = 'liteTest' # the path of database file
LOGS_ROOT_DIR = 'myTestLogs'


def loadYmlJson(file_path: str):
    """Get the given json or yaml file as a dict"""
    with open(file_path) as f:
        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            return yaml.load(f)
        elif file_path.endswith('.json'):
            return json.loads(f.read())
        else:
            return None


def dictToExperiment(experiment_dict):
    """Returns dict as Experiment
    Args:
        experiment_dict(dict): dictionary representation of Experiment
    Returns:
        experiment(Experiment): constructed Experiment
    """
    experiment_params = [Parameter(**param) for param in experiment_dict.pop('parameters')]
    compute_type = experiment_dict['compute']['type']
    if compute_type == 'ec2':
        compute = EC2Compute(**experiment_dict.pop('compute'))
    elif compute_type == 'local':
        compute = LocalCompute(**experiment_dict.pop('compute'))
    elif compute_type == 'PBSPro':
        compute = PBSProCompute(**experiment_dict.pop('compute'))

    return Experiment(parameters=experiment_params, compute=compute, **experiment_dict)


def getOrCreateExperiment(db_storage, experiment_dict):
    """Get or create experiment from dict
    Args:
        experiment_dict(dict): dictionary representation of Experiment
    Returns:
        experiment(dict): new or fetched Experiment as a dict
    """
    # print(experiment_dict)
    experiment = dictToExperiment(experiment_dict)
    # print(experiment)
    session = db_storage.Session()
    # print(experiment)
    try:
        experiment, _, _ = db_storage.getOrCreateExperiment(session, experiment)
        experiment_dict = experiment.asdict()
    except:
        session.rollback()
        raise
    finally:
        session.close()
    return experiment_dict


def get_from_dic(config, key):
    if key in config.keys():
        return config.get(key)
    else:
        return None


def getOptimizer(optimizer_config):
    #TODO: add support to more optimizer
    """Construct optimizer from a config dict
    
    Args:
        optimizer_config(dict): configuration for optimizer
    
    Returns:
        Optimizer
    """
    if optimizer_config == None:
        return BayesianOptimizer(n_init=2, n_iter=2)

    optimizer_type = optimizer_config.get('type')
    if optimizer_type == 'grid':
        num_configs_per_param = optimizer_config.get('num_configs_per_param')
        try:
            # num_configs_per_param = int(num_configs_per_param)
            num_configs_per_param = list(num_configs_per_param)
            return GridSearch(num_configs_per_param=num_configs_per_param)
        except:
            return None

    
    n_iter = get_from_dic(optimizer_config, 'n_iter')
    budget = get_from_dic(optimizer_config, 'budget')
    converge_thres = get_from_dic(optimizer_config, 'converge_thres')
    converge_steps = get_from_dic(optimizer_config, 'converge_steps')
    # n_iter = optimizer_config.get('n_iter')
    if n_iter is not None:
        n_iter = int(n_iter)
    if budget is not None:
        budget = float(budget)
    if converge_thres is not None:
        converge_thres = float(converge_thres)
    if converge_steps is not None:
        converge_steps = int(converge_steps)

    if optimizer_type == 'bayesopt':
        n_init = get_from_dic(optimizer_config, 'n_init')
        alpha = get_from_dic(optimizer_config, 'alpha')
        kappa = get_from_dic(optimizer_config, 'kappa')
        if n_init is not None:
            n_init = int(n_init)
        if alpha is not None:
            alpha = float(alpha)
        if kappa is not None:
            kappa = float(kappa)
        try:
            return BayesianOptimizer(n_init=n_init, n_iter=n_iter, alpha=alpha, kappa=kappa, 
                budget=budget, converge_thres=converge_thres, converge_steps=converge_steps)
        except:
            return None
    elif optimizer_type == 'random':
        random_seed = get_from_dic(optimizer_config, 'random_seed')
        if random_seed is not None:
            random_seed = int(random_seed)
        try:
            return RandomSearch(n_iter=n_iter, random_seed=random_seed,
                budget=budget, converge_thres=converge_thres, converge_steps=converge_steps)
        except:
            return None
    elif optimizer_type =='coordinate':
        random_seed = get_from_dic(optimizer_config, 'random_seed')
        if random_seed is not None:
            random_seed = int(random_seed)
        try:
            return CoordinateSearch(n_iter=n_iter, random_seed=random_seed,
                budget=budget, converge_thres=converge_thres, converge_steps=converge_steps)
        except:
            return None


def getObjective(obj_config):
    obj_info = {'obj_name': timeCmd, 'obj_params': {}}
    if obj_config is None:
        return obj_info
    else:
        # obj_info['obj_name'] = getattr(paropt.runner.parsl, get_from_dic(obj_config, 'obj_name'))
        print(obj_config)
        obj_info['obj_name'] = get_from_dic(obj_config, 'obj_name')
        obj_info['obj_params'] = get_from_dic(obj_config, 'obj_params')
        if obj_info['obj_params'] is None:
            obj_info['obj_params'] = {}
        if 'timeout' in obj_info['obj_params'].keys():
            obj_info['obj_params']['timeout'] = int(obj_info['obj_params']['timeout'])
        return obj_info


def startRunner(db_storage, experiment_dict, optimizer, obj_config):
    """Runs an experiment with paropt. This is the function used for job queueing

    Args:
        experiment_dict(dict): dict representation of experiment to run.
            Although it's a dict, the experiment it represents should already exist in the database.
        optimizer(Optimizer): Optimizer instance to use for running the experiment
    
    Returns:
        result(dict): result of the run
    
    Raises:
        Exception: when the runner fails, it will raise an exception with the message from the result
    """
    paropt.setConsoleLogger()
    experiment = dictToExperiment(experiment_dict)
    storage = db_storage

    if not os.path.exists(LOGS_ROOT_DIR):
        os.makedirs(LOGS_ROOT_DIR)
    po = ParslRunner(
        obj_func=getattr(paropt.runner.parsl, obj_config['obj_name']),
        optimizer=optimizer,
        obj_func_params=obj_config['obj_params'], 
        storage=storage,
        experiment=experiment,
        logs_root_dir=LOGS_ROOT_DIR)
    po.run(debug=True)
    # cleanup launched instances
    po.cleanup()

    # if po.run_result['success'] == False:
    #     raise Exception(po.run_result['message'])

    return po.run_result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Python cli for interacting with paropt service')
    parser.add_argument('--experiment', type=str, required=True, help='path to experiment yaml or json')
    # parser.add_argument('--optimizer', type=str, required=True, help='path to optimizer experiment or json')
    parser.add_argument('--maxwait', type=int, default=0, help='maximum time in minutes to wait for trial to finish; default is 0; < 0 waits forever')
    args = parser.parse_args()

    all_data = loadYmlJson(args.experiment)
    # get experiment data
    experiment_data = all_data['experiment']
    
    # get optimizer data
    optimizer_data = all_data['optimizer']
    obj_data = all_data['objective']

    if experiment_data == None:
        print(FILE_TYPE_MSG)
        sys.exit(1)
    
    optimizer = getOptimizer(optimizer_data)
    obj_config = getObjective(obj_data)

    print(experiment_data)
    print(optimizer_data)
    print(obj_config)
    # print('start')
    # db_storage = RelationalDB(DB_DIALECT, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME)
    try:
        db_storage = RelationalDB(DB_DIALECT, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME)
    except:
        print("\n---- Error ----")
        print("\nFail to create/connect to database file")
        sys.exit()

    try:
        experiment_dict = getOrCreateExperiment(db_storage, experiment_data)
    except:
        print("\n---- Error ----")
        print("\nFail to get/create experiment")
        sys.exit()

    print(experiment_dict)
    exp_id = experiment_dict['id']
    if not exp_id:
        print("\n---- Error ----")
        print("\nExpected experiment response to contain 'id'")
        sys.exit()

    run_result = startRunner(db_storage, experiment_dict, optimizer, obj_config)
    print(repr(run_result))