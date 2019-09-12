import multiprocessing
import atexit
import os
import time

from flask import current_app

import redis
from rq import Queue, Connection
from rq.registry import StartedJobRegistry, FailedJobRegistry, DeferredJobRegistry
from rq.job import Job
from rq.exceptions import NoSuchJobError

from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, in_production, getAWSConfig

import parsl

import paropt
from paropt.runner import ParslRunner
from paropt.storage import LocalFile, RelationalDB
from paropt.optimizer import BayesianOptimizer, GridSearch, RandomSearch, CoordinateSearch
from paropt.runner.parsl import *
from paropt.storage.entities import Parameter, Experiment, EC2Compute, LocalCompute


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
    obj_info = {'obj_name': timeCmd, 'obj_params': None}
    if obj_config is None:
        return obj_info
    else:
        obj_info['obj_name'] = get_from_dic(obj_config, 'obj_name')
        obj_info['obj_params'] = get_from_dic(obj_config, 'obj_params')
        return obj_info


class ParoptManager():
    """Manages paropt tasks and storage records using Redis queue and paropt storage"""
    _started = False
    db_storage = None

    @classmethod
    def start(cls):
        if cls._started:
            return
        cls.db_storage = RelationalDB(
            'postgresql',
            DB_USER,
            DB_PASSWORD,
            DB_HOST,
            DB_NAME
        )
        cls._started = True

    @classmethod
    def runTrials(cls, experiment_id, run_config):
        """Put experiment into job queue to be run

        Args:
            experiment_id(int): id of experiment to run
            run_config(dict): dict for how to config optimizer
        
        Returns:
            result(dict): result of attempt to add job to queue
        """
        if not cls._started:
            raise Exception("ParoptManager not started")

        # debugging get job (should be requested based on experiment id)
        job = cls.getExperimentJob(experiment_id)
        if job != None:
            return {'status': 'failed', 'message': 'Experiment already enqueued or running'}

        # check if experiment exists
        experiment = cls.getExperimentDict(experiment_id)
        if experiment == None:
            return {'status': 'failed', 'message': "Experiment not found with id {}".format(id)}
        
        optimizer = getOptimizer(run_config.get('optimizer'))
        obj_config = getObjective(run_config.get('objective'))
        if optimizer == None:
            tmp = run_config.get('optimizer')
            return {'status': 'failed', 'message': f'Invalid run configuration provided {tmp}, code: {optimizer[1]}'}
        
        # submit job to redis
        with Connection(redis.from_url(current_app.config['REDIS_URL'])):
            q = Queue()
            job = q.enqueue(
                f=cls._startRunner,
                args=(experiment, optimizer, obj_config),
                result_ttl=3600,
                job_timeout=-1,
                ttl=-1,
                meta={'experiment_id': str(experiment_id)})

        response_object = {
            'status': 'submitted',
            'job': cls.jobToDict(job)
        }
        return response_object

    @classmethod
    def getRunningExperiments(cls):
        """Returns experiments currently being run

        Returns:
            jobs(list): list of jobs that are being run
        """
        with Connection(redis.from_url(current_app.config['REDIS_URL'])) as conn:
            registry = StartedJobRegistry('default', connection=conn)
            return [Job.fetch(id, connection=conn) for id in registry.get_job_ids()]
    
    @classmethod
    def getFailedExperiments(cls):
        with Connection(redis.from_url(current_app.config['REDIS_URL'])) as conn:
            registry = FailedJobRegistry('default', connection=conn)
            return [Job.fetch(id, connection=conn) for id in registry.get_job_ids()]
    
    @classmethod
    def getDeferredExperiments(cls):
        with Connection(redis.from_url(current_app.config['REDIS_URL'])) as conn:
            registry = DeferredJobRegistry('default', connection=conn)
            return [Job.fetch(id, connection=conn) for id in registry.get_job_ids()]
    
    @classmethod
    def getQueuedJobs(cls):
        """Get a list of currently enqueued jobs"""
        with Connection(redis.from_url(current_app.config['REDIS_URL'])):
            q = Queue()
            return q.jobs # Gets a list of enqueued job instances
    
    @classmethod
    def getExperimentJob(cls, experiment_id):
        """Get job of an experiment - either enqueued or running"""

        # check running jobs
        running_jobs = cls.getRunningExperiments()
        for job in running_jobs:
            current_app.logger.info('Currently running: {}'.format(job))
            if job.get_status() != 'finished' and job.meta.get('experiment_id') == str(experiment_id):
                return job

        # check queued jobs
        queued_jobs = cls.getQueuedJobs()
        for job in queued_jobs:
            current_app.logger.info('Enqueued job: {}'.format(job))
            if job.get_status() != 'finished' and job.meta.get('experiment_id') == str(experiment_id):
                return job
        
        # job not found
        return None
    
    @classmethod
    def getJob(cls, job_id):
        with Connection(redis.from_url(current_app.config['REDIS_URL'])) as conn:
            job = None
            try:
                job = Job.fetch(job_id, connection=conn)
            except NoSuchJobError:
                pass
            except:
                raise
            return job
    
    @classmethod
    def jobToDict(cls, job):
        """Returns job as dict"""
        if job == None:
            return {}
        else:
            return {
                'job_id': job.get_id(),
                'job_status': job.get_status(),
                'job_result': job.result,
                'job_meta': job.meta,
                'job_exc_info': job.exc_info
            }
    
    @classmethod
    def getRunningExperiment(cls, experiment_id):
        """Gets the running job for experiment
        Args:
            experiment_id(str): id of experiment
        Returns:
            experiment(Job): is None if not currently running
        """
        jobs = cls.getRunningExperiments()
        for job in jobs:
            if job.get_status() != 'finished' and job.meta.get('experiment_id') == str(experiment_id):
                return job
        return None

    @classmethod
    def getTrials(cls, experiment_id):
        """Gets previous trials for experiment
        Args:
            experiment_id(str): id of experiment
        Returns:
            trials([]dict): List of trials in dict representation
        """
        session = cls.db_storage.Session()
        try:
            trials = cls.db_storage.getTrials(session, experiment_id)
            trials_dicts = [trial.asdict() for trial in trials]
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return trials_dicts

    @classmethod
    def dictToExperiment(cls, experiment_dict):
        """Returns dict as Experiment
        Args:
            experiment_dict(dict): dictionary representation of Experiment
        Returns:
            experiment(Experiment): constructed Experiment
        """
        experiment_params = [Parameter(**param) for param in experiment_dict.pop('parameters')]
        if in_production:
            compute = EC2Compute(**experiment_dict.pop('compute'))
        else:
            compute = LocalCompute(**experiment_dict.pop('compute'))
        return Experiment(parameters=experiment_params, compute=compute, **experiment_dict)
    
    @classmethod
    def getOrCreateExperiment(cls, experiment_dict):
        """Get or create experiment from dict
        Args:
            experiment_dict(dict): dictionary representation of Experiment
        Returns:
            experiment(dict): new or fetched Experiment as a dict
        """
        experiment = cls.dictToExperiment(experiment_dict)
        session = cls.db_storage.Session()
        try:
            experiment, _, _ = cls.db_storage.getOrCreateExperiment(session, experiment)
            experiment_dict = experiment.asdict()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return experiment_dict
    
    @classmethod
    def getExperimentDict(cls, experiment_id):
        """Get experiment as a dict
        Args:
            experiment_id(str): id of experiment
        Returns:
            experiment(Experiment): dict of found experiment; None if not found
        """
        session = cls.db_storage.Session()
        try:
            experiment = cls.db_storage.getExperiment(session, experiment_id)
            experiment_dict = experiment.asdict() if experiment != None else None
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return experiment_dict

    @classmethod
    def stopExperiment(cls, experiment_id):
        """Stops running an experiment
        Args:
            experiment_id(str): experiment to stop
        """
        return {'message': 'this functionality is not implemented yet'}

    @classmethod
    def _startRunner(cls, experiment_dict, optimizer, obj_config):
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
        experiment = cls.dictToExperiment(experiment_dict)
        storage = RelationalDB(
            'postgresql',
            DB_USER,
            DB_PASSWORD,
            DB_HOST,
            DB_NAME
        )

        po = ParslRunner(
            obj_func=obj_config['obj_name'],
            # obj_func=timeCmdLimit,
            optimizer=optimizer,
            obj_func_params=obj_config['obj_params'], 
            storage=storage,
            experiment=experiment,
            logs_root_dir='/var/log/paropt')
        po.run(debug=True)
        # cleanup launched instances
        po.cleanup()

        if po.run_result['success'] == False:
            raise Exception(po.run_result['message'])

        return po.run_result
